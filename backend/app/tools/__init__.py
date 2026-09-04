from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta
from typing import Any, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Appointment, Guest, Lead
from app.db.session import AsyncSessionLocal
from app.services.rag import search_knowledge

# Default clinic hours for MVP demo
DEFAULT_SLOTS = ["09:00", "10:00", "11:00", "13:00", "14:00", "15:00", "16:00", "17:00"]


def tool_definitions() -> list[dict[str, Any]]:
    """Internal tool schemas (Realtime-style flat function objects)."""
    return [
        {
            "type": "function",
            "name": "search_knowledge_base",
            "description": "Search the business knowledge base for prices, services, hours, policies, and FAQs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What the caller is asking about"},
                },
                "required": ["query"],
            },
        },
        {
            "type": "function",
            "name": "check_availability",
            "description": "Check open appointment slots for a given date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD, or relative like 'tomorrow' / 'Friday'",
                    },
                    "preference": {
                        "type": "string",
                        "description": "Optional preference such as morning/afternoon",
                    },
                },
                "required": ["date"],
            },
        },
        {
            "type": "function",
            "name": "book_appointment",
            "description": "Book an appointment after the caller confirms details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string"},
                    "phone": {"type": "string"},
                    "service": {"type": "string"},
                    "party_size": {
                        "type": "integer",
                        "description": "Number of guests / party size (restaurants) or 1 for clinics",
                    },
                    "date": {"type": "string", "description": "YYYY-MM-DD"},
                    "time": {"type": "string", "description": "HH:MM 24h"},
                    "notes": {"type": "string"},
                },
                "required": ["customer_name", "date", "time"],
            },
        },
        {
            "type": "function",
            "name": "lookup_guest",
            "description": "Look up a returning guest by phone or name for personalization.",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string"},
                    "name": {"type": "string"},
                },
            },
        },
        {
            "type": "function",
            "name": "cancel_appointment",
            "description": "Cancel an existing appointment by customer name and date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string"},
                    "date": {"type": "string"},
                    "time": {"type": "string"},
                },
                "required": ["customer_name", "date"],
            },
        },
        {
            "type": "function",
            "name": "create_lead",
            "description": "Capture a lead when the caller is interested but not booking yet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "phone": {"type": "string"},
                    "email": {"type": "string"},
                    "intent": {"type": "string"},
                    "notes": {"type": "string"},
                },
                "required": ["intent"],
            },
        },
        {
            "type": "function",
            "name": "transfer_to_human",
            "description": "Request human handoff / callback when the caller asks for a person.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string"},
                    "caller_name": {"type": "string"},
                    "callback_number": {"type": "string"},
                },
                "required": ["reason"],
            },
        },
    ]


def chat_tool_definitions() -> list[dict[str, Any]]:
    """Groq / OpenAI Chat Completions tool schema wrapper."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["parameters"],
            },
        }
        for t in tool_definitions()
    ]


def _parse_relative_date(value: str) -> date:
    value = (value or "").strip().lower()
    today = date.today()
    if value in {"today"}:
        return today
    if value in {"tomorrow"}:
        return today + timedelta(days=1)
    weekdays = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }
    for name, idx in weekdays.items():
        if name in value:
            delta = (idx - today.weekday()) % 7
            delta = 7 if delta == 0 else delta
            return today + timedelta(days=delta)
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return today + timedelta(days=1)


def _parse_time(value: str) -> time:
    value = value.strip()
    for fmt in ("%H:%M", "%H:%M:%S", "%I:%M %p", "%I %p"):
        try:
            return datetime.strptime(value, fmt).time().replace(second=0, microsecond=0)
        except ValueError:
            continue
    # fallback e.g. 3pm
    cleaned = value.lower().replace(".", "")
    if cleaned.endswith("pm") or cleaned.endswith("am"):
        try:
            return datetime.strptime(cleaned.upper(), "%I%p").time()
        except ValueError:
            pass
    return time(15, 0)


def _filter_slots(slots: list[str], preference: Optional[str]) -> list[str]:
    if not preference:
        return slots
    pref = preference.lower()
    if "morning" in pref:
        return [s for s in slots if int(s.split(":")[0]) < 12]
    if "afternoon" in pref:
        return [s for s in slots if 12 <= int(s.split(":")[0]) < 17]
    if "evening" in pref:
        return [s for s in slots if int(s.split(":")[0]) >= 17]
    return slots


class ToolExecutor:
    def __init__(self, agent_id: int, business_id: int, caller_number: Optional[str] = None):
        self.agent_id = agent_id
        self.business_id = business_id
        self.caller_number = caller_number
        self.last_outcome: Optional[str] = None
        self.transcript_notes: list[str] = []

    async def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        handler = {
            "search_knowledge_base": self.search_knowledge_base,
            "check_availability": self.check_availability,
            "book_appointment": self.book_appointment,
            "cancel_appointment": self.cancel_appointment,
            "create_lead": self.create_lead,
            "transfer_to_human": self.transfer_to_human,
            "lookup_guest": self.lookup_guest,
        }.get(name)
        if not handler:
            return {"error": f"Unknown tool: {name}"}
        return await handler(**arguments)

    async def search_knowledge_base(self, query: str) -> dict[str, Any]:
        async with AsyncSessionLocal() as db:
            hits = await search_knowledge(db, self.agent_id, query)
        if not hits:
            return {
                "found": False,
                "message": "No matching knowledge found. Say you are unsure and offer to take a message.",
            }
        return {
            "found": True,
            "results": hits,
        }

    async def check_availability(self, date: str, preference: Optional[str] = None) -> dict[str, Any]:
        day = _parse_relative_date(date)
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Appointment).where(
                    and_(
                        Appointment.business_id == self.business_id,
                        Appointment.date == day,
                        Appointment.status == "booked",
                    )
                )
            )
            booked = {a.time.strftime("%H:%M") for a in result.scalars().all()}

        open_slots = [s for s in DEFAULT_SLOTS if s not in booked]
        open_slots = _filter_slots(open_slots, preference)
        return {
            "date": day.isoformat(),
            "available": bool(open_slots),
            "slots": open_slots,
        }

    async def book_appointment(
        self,
        customer_name: str,
        date: str,
        time: str,
        phone: Optional[str] = None,
        service: Optional[str] = None,
        notes: Optional[str] = None,
        party_size: int = 1,
    ) -> dict[str, Any]:
        day = _parse_relative_date(date)
        slot = _parse_time(time)
        party = max(1, int(party_size or 1))
        phone_val = phone or self.caller_number
        async with AsyncSessionLocal() as db:
            existing = await db.execute(
                select(Appointment).where(
                    and_(
                        Appointment.business_id == self.business_id,
                        Appointment.date == day,
                        Appointment.time == slot,
                        Appointment.status == "booked",
                    )
                )
            )
            if existing.scalar_one_or_none():
                return {"success": False, "error": "That slot is no longer available."}

            appt = Appointment(
                business_id=self.business_id,
                customer_name=customer_name,
                phone=phone_val,
                service=service,
                party_size=party,
                date=day,
                time=slot,
                notes=notes,
                status="booked",
                source="voice",
            )
            db.add(appt)

            # Upsert guest brain
            guest = None
            if phone_val:
                gres = await db.execute(
                    select(Guest).where(
                        Guest.business_id == self.business_id,
                        Guest.phone == phone_val,
                    )
                )
                guest = gres.scalar_one_or_none()
            if guest is None:
                guest = Guest(
                    business_id=self.business_id,
                    name=customer_name,
                    phone=phone_val,
                    visit_count=1,
                    last_visit_at=datetime.utcnow(),
                )
                db.add(guest)
            else:
                guest.name = customer_name or guest.name
                guest.visit_count = (guest.visit_count or 0) + 1
                guest.last_visit_at = datetime.utcnow()

            await db.commit()
            await db.refresh(appt)
            self.last_outcome = "Appointment booked"
            return {
                "success": True,
                "appointment_id": appt.id,
                "customer_name": customer_name,
                "date": day.isoformat(),
                "time": slot.strftime("%H:%M"),
                "service": service,
                "party_size": party,
            }

    async def lookup_guest(
        self,
        phone: Optional[str] = None,
        name: Optional[str] = None,
    ) -> dict[str, Any]:
        async with AsyncSessionLocal() as db:
            stmt = select(Guest).where(Guest.business_id == self.business_id)
            if phone:
                stmt = stmt.where(Guest.phone == phone)
            elif name:
                stmt = stmt.where(Guest.name.ilike(name))
            else:
                return {"found": False, "message": "Provide phone or name"}
            result = await db.execute(stmt)
            guest = result.scalars().first()
            if not guest:
                return {"found": False}
            return {
                "found": True,
                "name": guest.name,
                "phone": guest.phone,
                "email": guest.email,
                "preferences": guest.preferences,
                "visit_count": guest.visit_count,
                "notes": guest.notes,
            }

    async def cancel_appointment(
        self,
        customer_name: str,
        date: str,
        time: Optional[str] = None,
    ) -> dict[str, Any]:
        day = _parse_relative_date(date)
        async with AsyncSessionLocal() as db:
            stmt = select(Appointment).where(
                and_(
                    Appointment.business_id == self.business_id,
                    Appointment.date == day,
                    Appointment.customer_name.ilike(customer_name),
                    Appointment.status == "booked",
                )
            )
            if time:
                stmt = stmt.where(Appointment.time == _parse_time(time))
            result = await db.execute(stmt)
            appt = result.scalars().first()
            if not appt:
                return {"success": False, "error": "No matching appointment found."}
            appt.status = "cancelled"
            await db.commit()
            self.last_outcome = "Appointment cancelled"
            return {"success": True, "appointment_id": appt.id}

    async def create_lead(
        self,
        intent: str,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> dict[str, Any]:
        async with AsyncSessionLocal() as db:
            lead = Lead(
                business_id=self.business_id,
                name=name,
                phone=phone or self.caller_number,
                email=email,
                intent=intent,
                notes=notes,
            )
            db.add(lead)
            await db.commit()
            await db.refresh(lead)
            self.last_outcome = "Lead captured"
            return {"success": True, "lead_id": lead.id}

    async def transfer_to_human(
        self,
        reason: str,
        caller_name: Optional[str] = None,
        callback_number: Optional[str] = None,
    ) -> dict[str, Any]:
        # MVP: create a callback lead instead of live warm transfer
        result = await self.create_lead(
            intent="human_transfer_request",
            name=caller_name,
            phone=callback_number or self.caller_number,
            notes=f"Caller requested human handoff. Reason: {reason}",
        )
        self.last_outcome = "Transferred"
        return {
            "success": True,
            "mode": "callback_request",
            "message": "A team member will call the customer back shortly.",
            "lead": result,
        }


def parse_tool_arguments(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw or "{}")
        except json.JSONDecodeError:
            return {}
    return {}
