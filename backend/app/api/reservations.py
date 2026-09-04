from datetime import date, time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Appointment, Business, Guest, User
from app.db.session import get_db
from app.services.auth import get_current_user
from app.tools import ToolExecutor

router = APIRouter(tags=["reservations"])


class GuestOut(BaseModel):
    id: int
    business_id: int
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    preferences: Optional[str] = None
    visit_count: int
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class ReservationOut(BaseModel):
    id: int
    business_id: int
    customer_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    service: Optional[str] = None
    party_size: int = 1
    date: date
    time: time
    status: str
    source: str = "voice"
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class PublicAvailabilityIn(BaseModel):
    date: date
    preference: Optional[str] = None


class PublicBookIn(BaseModel):
    customer_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    party_size: int = Field(default=2, ge=1, le=20)
    date: date
    time: str
    notes: Optional[str] = None
    service: Optional[str] = "Reservation"


@router.get("/reservations", response_model=list[ReservationOut])
async def list_reservations(
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


@router.get("/guests", response_model=list[GuestOut])
async def list_guests(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Guest)
        .join(Business, Business.id == Guest.business_id)
        .where(Business.user_id == user.id)
        .order_by(Guest.id.desc())
    )
    return list(result.scalars().all())


@router.get("/public/businesses/{business_id}")
async def public_business(business_id: int, db: AsyncSession = Depends(get_db)):
    biz = await db.get(Business, business_id)
    if not biz:
        raise HTTPException(status_code=404, detail="Business not found")
    return {
        "id": biz.id,
        "name": biz.name,
        "industry": biz.industry,
        "address": biz.address,
        "timezone": biz.timezone,
    }


@router.post("/public/businesses/{business_id}/availability")
async def public_availability(
    business_id: int,
    payload: PublicAvailabilityIn,
    db: AsyncSession = Depends(get_db),
):
    biz = await db.get(Business, business_id)
    if not biz:
        raise HTTPException(status_code=404, detail="Business not found")
    tools = ToolExecutor(agent_id=0, business_id=business_id)
    return await tools.check_availability(payload.date.isoformat(), payload.preference)


@router.post("/public/businesses/{business_id}/book", response_model=ReservationOut)
async def public_book(
    business_id: int,
    payload: PublicBookIn,
    db: AsyncSession = Depends(get_db),
):
    biz = await db.get(Business, business_id)
    if not biz:
        raise HTTPException(status_code=404, detail="Business not found")
    tools = ToolExecutor(agent_id=0, business_id=business_id)
    result = await tools.book_appointment(
        customer_name=payload.customer_name,
        date=payload.date.isoformat(),
        time=payload.time,
        phone=payload.phone,
        service=payload.service,
        notes=payload.notes,
        party_size=payload.party_size,
    )
    if not result.get("success"):
        raise HTTPException(status_code=409, detail=result.get("error", "Booking failed"))
    appt = await db.get(Appointment, result["appointment_id"])
    if appt:
        appt.source = "widget"
        appt.email = payload.email
        await db.commit()
        await db.refresh(appt)
    return appt
