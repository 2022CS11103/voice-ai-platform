from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import Agent, Business, User
from app.db.session import get_db
from app.services.auth import get_current_user
from app.services.groq_llm import run_agent_turn
from app.services.prompt import build_system_prompt
from app.tools import ToolExecutor

router = APIRouter(prefix="/agents", tags=["agents-test"])


class TestChatIn(BaseModel):
    message: str = Field(min_length=1)
    history: list[dict] = Field(default_factory=list)


class TestChatOut(BaseModel):
    reply: str
    history: list[dict]


@router.post("/{agent_id}/test", response_model=TestChatOut)
async def test_agent_chat(
    agent_id: int,
    payload: TestChatIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Browser test chat — same tools/RAG as phone agent, no Twilio needed."""
    settings = get_settings()
    if not settings.groq_api_key:
        raise HTTPException(status_code=400, detail="GROQ_API_KEY is not configured")

    result = await db.execute(
        select(Agent, Business)
        .join(Business, Business.id == Agent.business_id)
        .where(Agent.id == agent_id, Business.user_id == user.id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent, business = row

    system_prompt = agent.system_prompt or build_system_prompt(agent, business)
    system_prompt += (
        "\n\nYou are in a dashboard test chat (not a phone call). Be concise. "
        "Answer based on their latest message, then ask exactly one smart follow-up "
        "question. Use tools for facts, availability, guests, and booking."
    )
    tools = ToolExecutor(agent.id, business.id, caller_number=None)
    history = [h for h in payload.history if h.get("role") in ("user", "assistant")][-16:]

    reply = await run_agent_turn(
        system_prompt=system_prompt,
        history=history,
        user_text=payload.message,
        tools=tools,
    )
    new_history = [
        *history,
        {"role": "user", "content": payload.message},
        {"role": "assistant", "content": reply},
    ]
    return TestChatOut(reply=reply, history=new_history)
