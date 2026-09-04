import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api import agents, auth, calls, knowledge, reservations, telephony, test_chat
from app.config import get_settings, refresh_settings
from app.db.models import Agent, Business, User
from app.db.session import AsyncSessionLocal, init_db
from app.services.auth import hash_password
from app.services.prompt import build_system_prompt
from app.services.rag import ingest_text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = refresh_settings()

DEMO_KNOWLEDGE = """
ABC Dental Clinic — Business Information

Address: 123 Main Street
Phone: (415) 555-0100
Opening hours: Monday to Friday 9 AM - 6 PM. Closed weekends.

Services and pricing:
- Dental cleaning: $80
- Consultation: $50
- Root canal: $450
- Tooth extraction: $200
- Teeth whitening: $350
- Emergency visit: $120

Cancellation policy:
Appointments must be cancelled at least 24 hours in advance.
Late cancellations may incur a $40 fee.

Insurance:
We accept most major dental insurance plans. Patients should bring their insurance card.

Booking rules:
New patients should arrive 15 minutes early for paperwork.
"""


async def seed_demo_data() -> None:
    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(User).where(User.email == settings.demo_email))
        user = existing.scalar_one_or_none()
        if user:
            # Keep Twilio number in sync with .env for existing installs
            if settings.twilio_phone_number:
                result = await db.execute(
                    select(Agent).where(Agent.name == "Sarah").order_by(Agent.id.asc())
                )
                agent = result.scalars().first()
                if agent:
                    changed = False
                    if agent.phone_number != settings.twilio_phone_number:
                        agent.phone_number = settings.twilio_phone_number
                        changed = True
                    biz = await db.get(Business, agent.business_id)
                    if biz:
                        agent.system_prompt = build_system_prompt(agent, biz)
                        changed = True
                    if changed:
                        await db.commit()
            if not user.phone:
                user.phone = "+10000000000"
                await db.commit()
            # Never block a real user's India number on the demo account
            if user.phone in {"+918318762518", "8318762518", "+918318762518"}:
                user.phone = "+10000000000"
                await db.commit()
            return

        user = User(
            email=settings.demo_email,
            phone="+10000000000",
            name=settings.demo_name,
            hashed_password=hash_password(settings.demo_password),
        )
        db.add(user)
        await db.flush()

        business = Business(
            user_id=user.id,
            name="ABC Dental Clinic",
            industry="healthcare",
            timezone="America/Los_Angeles",
            address="123 Main Street",
            phone=settings.twilio_phone_number or "+1XXXXXXXXXX",
        )
        db.add(business)
        await db.flush()

        agent = Agent(
            business_id=business.id,
            name="Sarah",
            purpose="Handle patient inquiries and appointment booking",
            personality="friendly",
            voice=settings.tts_voice,
            language="English",
            greeting="Hi! Thanks for calling ABC Dental. How can I help you today?",
            phone_number=settings.twilio_phone_number or None,
            status="active",
            capabilities={
                "answer_questions": True,
                "book_appointments": True,
                "capture_leads": True,
                "transfer_calls": True,
                "take_orders": False,
            },
        )
        agent.system_prompt = build_system_prompt(agent, business)
        db.add(agent)
        await db.commit()
        await db.refresh(agent)

        await ingest_text(
            db,
            agent_id=agent.id,
            content=DEMO_KNOWLEDGE,
            filename="clinic_information.txt",
            source_type="seed",
        )
        logger.info("Seeded demo user %s / agent Sarah", settings.demo_email)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    await seed_demo_data()
    yield


app = FastAPI(
    title="Voice AI Platform",
    description="Multi-tenant inbound voice AI agents for businesses",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(agents.router, prefix="/api")
app.include_router(test_chat.router, prefix="/api")
app.include_router(knowledge.router, prefix="/api")
app.include_router(calls.router, prefix="/api")
app.include_router(reservations.router, prefix="/api")
app.include_router(telephony.router)


@app.get("/health")
async def health():
    s = refresh_settings()
    return {
        "status": "ok",
        "provider": "groq",
        "version": "twilio-fix-1",
        "groq_configured": bool(s.groq_api_key),
        "twilio_configured": s.twilio_ready,
        "twilio_sid_ok": (s.twilio_account_sid or "").startswith("AC"),
        "twilio_token_set": bool(s.twilio_auth_token),
        "twilio_phone": s.twilio_phone_number or None,
        "public_base_url": s.public_base_url,
    }


@app.get("/")
async def root():
    return {
        "message": "Voice AI Platform API",
        "docs": "/docs",
        "telephony_webhook": "/telephony/incoming",
        "media_stream": "/telephony/stream",
    }
