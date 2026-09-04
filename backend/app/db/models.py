from __future__ import annotations

from datetime import date, datetime, time
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import get_settings
from app.db.session import Base

settings = get_settings()

# pgvector Vector type when available; JSON list fallback for SQLite MVP
if settings.use_pgvector:
    from pgvector.sqlalchemy import Vector

    EmbeddingType = Vector(1536)
else:
    EmbeddingType = JSON


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), unique=True, index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    businesses: Mapped[list["Business"]] = relationship(back_populates="owner")


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    industry: Mapped[str] = mapped_column(String(100), default="healthcare")
    timezone: Mapped[str] = mapped_column(String(64), default="America/Los_Angeles")
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner: Mapped["User"] = relationship(back_populates="businesses")
    agents: Mapped[list["Agent"]] = relationship(back_populates="business")
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="business")
    leads: Mapped[list["Lead"]] = relationship(back_populates="business")


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    purpose: Mapped[str] = mapped_column(Text, default="Handle customer inquiries and appointments")
    personality: Mapped[str] = mapped_column(String(50), default="friendly")
    voice: Mapped[str] = mapped_column(String(50), default="alloy")
    language: Mapped[str] = mapped_column(String(20), default="English")
    speaking_speed: Mapped[float] = mapped_column(Float, default=1.0)
    greeting: Mapped[str] = mapped_column(
        Text,
        default="Hi! Thanks for calling. How can I help you today?",
    )
    system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    capabilities: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=lambda: {
            "answer_questions": True,
            "book_appointments": True,
            "capture_leads": True,
            "transfer_calls": True,
            "take_orders": False,
        },
    )
    status: Mapped[str] = mapped_column(String(30), default="active")
    phone_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    escalation_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    after_hours_behavior: Mapped[str] = mapped_column(String(50), default="take_message")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    business: Mapped["Business"] = relationship(back_populates="agents")
    documents: Mapped[list["Document"]] = relationship(back_populates="agent")
    chunks: Mapped[list["KnowledgeChunk"]] = relationship(back_populates="agent")
    calls: Mapped[list["Call"]] = relationship(back_populates="agent")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(50), default="upload")
    file_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="processing")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    agent: Mapped["Agent"] = relationship(back_populates="documents")
    chunks: Mapped[list["KnowledgeChunk"]] = relationship(back_populates="document")


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[Optional[int]] = mapped_column(ForeignKey("documents.id"), nullable=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), index=True)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[Any] = mapped_column(EmbeddingType, nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document: Mapped[Optional["Document"]] = relationship(back_populates="chunks")
    agent: Mapped["Agent"] = relationship(back_populates="chunks")


class Call(Base):
    __tablename__ = "calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), index=True)
    caller_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    twilio_call_sid: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(30), default="in_progress")
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    outcome: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    intent: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sentiment: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    successful: Mapped[bool] = mapped_column(Boolean, default=True)

    agent: Mapped["Agent"] = relationship(back_populates="calls")
    messages: Mapped[list["Message"]] = relationship(back_populates="call")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    call_id: Mapped[int] = mapped_column(ForeignKey("calls.id"), index=True)
    role: Mapped[str] = mapped_column(String(30))
    content: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    call: Mapped["Call"] = relationship(back_populates="messages")


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (UniqueConstraint("business_id", "date", "time", name="uq_slot"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    customer_name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    service: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    party_size: Mapped[int] = mapped_column(Integer, default=1)
    date: Mapped[date] = mapped_column(Date)
    time: Mapped[time] = mapped_column(Time)
    status: Mapped[str] = mapped_column(String(30), default="booked")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="voice")  # voice | widget | chat
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    business: Mapped["Business"] = relationship(back_populates="appointments")


class Guest(Base):
    """Unified guest brain — shared across voice, widget, and staff."""

    __tablename__ = "guests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    preferences: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    visit_count: Mapped[int] = mapped_column(Integer, default=0)
    last_visit_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    intent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    business: Mapped["Business"] = relationship(back_populates="leads")
