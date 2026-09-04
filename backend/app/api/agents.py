from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import Agent, Business, Call, User
from app.db.session import get_db
from app.schemas import AgentCreate, AgentOut, AgentUpdate
from app.services.auth import get_current_user
from app.services.prompt import build_system_prompt

router = APIRouter(prefix="/agents", tags=["agents"])


async def _owned_agent(db: AsyncSession, user: User, agent_id: int) -> Agent:
    result = await db.execute(
        select(Agent)
        .join(Business, Business.id == Agent.business_id)
        .where(Agent.id == agent_id, Business.user_id == user.id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


async def _agent_stats(db: AsyncSession, agent_id: int) -> tuple[int, float, float]:
    result = await db.execute(select(Call).where(Call.agent_id == agent_id))
    calls = list(result.scalars().all())
    if not calls:
        return 0, 0.0, 0.0
    count = len(calls)
    avg_dur = sum(c.duration_seconds for c in calls) / count
    success = sum(1 for c in calls if c.successful) / count * 100
    return count, avg_dur, success


async def _ensure_phone(db: AsyncSession, agent: Agent) -> Agent:
    settings = get_settings()
    if not agent.phone_number and settings.twilio_phone_number:
        agent.phone_number = settings.twilio_phone_number
        await db.commit()
        await db.refresh(agent)
    return agent


def _to_out(agent: Agent, business_name: str, stats: tuple[int, float, float]) -> AgentOut:
    count, avg_dur, success = stats
    return AgentOut(
        id=agent.id,
        business_id=agent.business_id,
        name=agent.name,
        purpose=agent.purpose,
        personality=agent.personality,
        voice=agent.voice,
        language=agent.language,
        speaking_speed=agent.speaking_speed,
        greeting=agent.greeting,
        system_prompt=agent.system_prompt,
        capabilities=agent.capabilities or {},
        status=agent.status,
        phone_number=agent.phone_number,
        escalation_number=agent.escalation_number,
        after_hours_behavior=agent.after_hours_behavior,
        created_at=agent.created_at,
        business_name=business_name,
        call_count=count,
        avg_duration_seconds=avg_dur,
        success_rate=success,
    )


@router.get("", response_model=list[AgentOut])
async def list_agents(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Agent, Business)
        .join(Business, Business.id == Agent.business_id)
        .where(Business.user_id == user.id)
        .order_by(Agent.id.desc())
    )
    rows = result.all()
    out = []
    for agent, business in rows:
        agent = await _ensure_phone(db, agent)
        stats = await _agent_stats(db, agent.id)
        out.append(_to_out(agent, business.name, stats))
    return out


@router.post("", response_model=AgentOut)
async def create_agent(
    payload: AgentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    biz_result = await db.execute(
        select(Business).where(Business.user_id == user.id).order_by(Business.id)
    )
    business = biz_result.scalars().first()
    if not business:
        business = Business(
            user_id=user.id, name=payload.business_name, industry=payload.industry
        )
        db.add(business)
        await db.flush()
    else:
        business.name = payload.business_name
        business.industry = payload.industry
        business.timezone = payload.timezone
        if payload.address:
            business.address = payload.address

    greeting = (
        payload.greeting
        or f"Hi! Thanks for calling {payload.business_name}. How can I help you today?"
    )
    agent = Agent(
        business_id=business.id,
        name=payload.agent_name,
        purpose=payload.purpose,
        personality=payload.personality,
        voice=payload.voice,
        language=payload.language,
        greeting=greeting,
        phone_number=settings.twilio_phone_number or None,
        capabilities=payload.capabilities
        or {
            "answer_questions": True,
            "book_appointments": True,
            "capture_leads": True,
            "transfer_calls": True,
            "take_orders": False,
        },
        status="active",
    )
    agent.system_prompt = build_system_prompt(agent, business)
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return _to_out(agent, business.name, (0, 0.0, 0.0))


@router.get("/{agent_id}", response_model=AgentOut)
async def get_agent(
    agent_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = await _owned_agent(db, user, agent_id)
    agent = await _ensure_phone(db, agent)
    biz = await db.get(Business, agent.business_id)
    stats = await _agent_stats(db, agent.id)
    return _to_out(agent, biz.name if biz else "", stats)


@router.patch("/{agent_id}", response_model=AgentOut)
async def update_agent(
    agent_id: int,
    payload: AgentUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = await _owned_agent(db, user, agent_id)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(agent, key, value)

    biz = await db.get(Business, agent.business_id)
    if biz and "system_prompt" not in data:
        agent.system_prompt = build_system_prompt(agent, biz)
    await db.commit()
    await db.refresh(agent)
    stats = await _agent_stats(db, agent.id)
    return _to_out(agent, biz.name if biz else "", stats)
