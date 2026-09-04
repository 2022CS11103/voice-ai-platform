from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Agent, Appointment, Business, Call, Lead, Message, User
from app.db.session import get_db
from app.schemas import (
    AnalyticsOut,
    AppointmentCreate,
    AppointmentOut,
    AvailabilityCheck,
    CallDetailOut,
    CallOut,
    LeadCreate,
    LeadOut,
    MessageOut,
)
from app.services.auth import get_current_user
from app.tools import ToolExecutor

router = APIRouter(tags=["calls"])


@router.get("/calls", response_model=list[CallOut])
async def list_calls(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Call, Agent)
        .join(Agent, Agent.id == Call.agent_id)
        .join(Business, Business.id == Agent.business_id)
        .where(Business.user_id == user.id)
        .order_by(Call.id.desc())
        .limit(100)
    )
    out = []
    for call, agent in result.all():
        item = CallOut.model_validate(call)
        item.agent_name = agent.name
        out.append(item)
    return out


@router.get("/calls/{call_id}", response_model=CallDetailOut)
async def get_call(
    call_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Call, Agent)
        .join(Agent, Agent.id == Call.agent_id)
        .join(Business, Business.id == Agent.business_id)
        .where(Call.id == call_id, Business.user_id == user.id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Call not found")
    call, agent = row
    msgs = await db.execute(
        select(Message).where(Message.call_id == call.id).order_by(Message.id.asc())
    )
    detail = CallDetailOut.model_validate(call)
    detail.agent_name = agent.name
    detail.messages = [MessageOut.model_validate(m) for m in msgs.scalars().all()]
    return detail


@router.get("/analytics", response_model=AnalyticsOut)
async def analytics(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    calls_result = await db.execute(
        select(Call)
        .join(Agent, Agent.id == Call.agent_id)
        .join(Business, Business.id == Agent.business_id)
        .where(Business.user_id == user.id)
    )
    calls = list(calls_result.scalars().all())
    total = len(calls)
    successful = sum(1 for c in calls if c.successful and (c.outcome or "") != "Transferred")
    transferred = sum(1 for c in calls if (c.outcome or "") == "Transferred")
    failed = sum(1 for c in calls if not c.successful)
    avg = (sum(c.duration_seconds for c in calls) / total) if total else 0.0

    biz_ids = (
        await db.execute(select(Business.id).where(Business.user_id == user.id))
    ).scalars().all()
    appt_count = 0
    lead_count = 0
    if biz_ids:
        appt_count = (
            await db.execute(
                select(func.count()).select_from(Appointment).where(Appointment.business_id.in_(biz_ids))
            )
        ).scalar_one()
        lead_count = (
            await db.execute(select(func.count()).select_from(Lead).where(Lead.business_id.in_(biz_ids)))
        ).scalar_one()

    return AnalyticsOut(
        total_calls=total,
        successful_calls=successful,
        transferred=transferred,
        failed=failed,
        avg_duration_seconds=avg,
        appointments=appt_count,
        leads_captured=lead_count,
    )


@router.post("/appointments/check")
async def check_availability(
    payload: AvailabilityCheck,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    biz = await db.get(Business, payload.business_id)
    if not biz or biz.user_id != user.id:
        raise HTTPException(status_code=404, detail="Business not found")
    tools = ToolExecutor(agent_id=0, business_id=payload.business_id)
    return await tools.check_availability(payload.date.isoformat(), payload.preference)


@router.post("/appointments", response_model=AppointmentOut)
async def create_appointment(
    payload: AppointmentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    biz = await db.get(Business, payload.business_id)
    if not biz or biz.user_id != user.id:
        raise HTTPException(status_code=404, detail="Business not found")
    tools = ToolExecutor(agent_id=0, business_id=payload.business_id)
    result = await tools.book_appointment(
        customer_name=payload.customer_name,
        date=payload.date.isoformat(),
        time=payload.time.strftime("%H:%M"),
        phone=payload.phone,
        service=payload.service,
        notes=payload.notes,
    )
    if not result.get("success"):
        raise HTTPException(status_code=409, detail=result.get("error", "Booking failed"))
    appt = await db.get(Appointment, result["appointment_id"])
    return appt


@router.get("/appointments", response_model=list[AppointmentOut])
async def list_appointments(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Appointment)
        .join(Business, Business.id == Appointment.business_id)
        .where(Business.user_id == user.id)
        .order_by(Appointment.id.desc())
    )
    return list(result.scalars().all())


@router.post("/leads", response_model=LeadOut)
async def create_lead(
    payload: LeadCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    biz = await db.get(Business, payload.business_id)
    if not biz or biz.user_id != user.id:
        raise HTTPException(status_code=404, detail="Business not found")
    lead = Lead(**payload.model_dump())
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    return lead


@router.get("/leads", response_model=list[LeadOut])
async def list_leads(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Lead)
        .join(Business, Business.id == Lead.business_id)
        .where(Business.user_id == user.id)
        .order_by(Lead.id.desc())
    )
    return list(result.scalars().all())
