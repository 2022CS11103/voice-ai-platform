from datetime import date, datetime, time
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SignupRequest(BaseModel):
    email: EmailStr
    phone: str = Field(min_length=10, max_length=20)
    password: str = Field(min_length=6, max_length=128)
    name: str = Field(min_length=2, max_length=100)

    @field_validator("email")
    @classmethod
    def email_must_be_valid(cls, v: EmailStr) -> str:
        from app.services.validators import validate_business_email

        return validate_business_email(str(v))

    @field_validator("phone")
    @classmethod
    def phone_must_be_valid(cls, v: str) -> str:
        from app.services.validators import normalize_phone

        return normalize_phone(v)

    @field_validator("name")
    @classmethod
    def name_clean(cls, v: str) -> str:
        cleaned = " ".join((v or "").split())
        if len(cleaned) < 2:
            raise ValueError("Name is required")
        return cleaned


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def email_normalize(cls, v: EmailStr) -> str:
        from app.services.validators import normalize_email

        return normalize_email(str(v))


class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: str
    phone: Optional[str] = None

    model_config = {"from_attributes": True}


class AgentCreate(BaseModel):
    business_name: str
    industry: str = "healthcare"
    agent_name: str
    purpose: str = "Handle customer inquiries and appointment booking"
    personality: str = "friendly"
    voice: str = "alloy"
    language: str = "English"
    greeting: Optional[str] = None
    capabilities: Optional[dict[str, bool]] = None
    address: Optional[str] = None
    timezone: str = "America/Los_Angeles"


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    purpose: Optional[str] = None
    personality: Optional[str] = None
    voice: Optional[str] = None
    language: Optional[str] = None
    speaking_speed: Optional[float] = None
    greeting: Optional[str] = None
    capabilities: Optional[dict[str, bool]] = None
    status: Optional[str] = None
    phone_number: Optional[str] = None
    escalation_number: Optional[str] = None
    after_hours_behavior: Optional[str] = None
    system_prompt: Optional[str] = None


class AgentOut(BaseModel):
    id: int
    business_id: int
    name: str
    purpose: str
    personality: str
    voice: str
    language: str
    speaking_speed: float
    greeting: str
    system_prompt: Optional[str]
    capabilities: dict[str, Any]
    status: str
    phone_number: Optional[str]
    escalation_number: Optional[str]
    after_hours_behavior: str
    created_at: datetime
    business_name: Optional[str] = None
    call_count: int = 0
    avg_duration_seconds: float = 0
    success_rate: float = 0

    model_config = {"from_attributes": True}


class DocumentOut(BaseModel):
    id: int
    agent_id: int
    filename: str
    source_type: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeTextIn(BaseModel):
    title: str = "Manual knowledge"
    content: str


class WebsiteImportIn(BaseModel):
    url: str


class CallOut(BaseModel):
    id: int
    agent_id: int
    caller_number: Optional[str]
    started_at: datetime
    ended_at: Optional[datetime]
    duration_seconds: int
    status: str
    summary: Optional[str]
    outcome: Optional[str]
    intent: Optional[str]
    sentiment: Optional[str]
    successful: bool
    agent_name: Optional[str] = None

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    timestamp: datetime

    model_config = {"from_attributes": True}


class CallDetailOut(CallOut):
    messages: list[MessageOut] = []


class AppointmentCreate(BaseModel):
    business_id: int
    customer_name: str
    phone: Optional[str] = None
    service: Optional[str] = None
    date: date
    time: time
    notes: Optional[str] = None


class AppointmentOut(BaseModel):
    id: int
    business_id: int
    customer_name: str
    phone: Optional[str]
    service: Optional[str]
    date: date
    time: time
    status: str
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class AvailabilityCheck(BaseModel):
    business_id: int
    date: date
    preference: Optional[str] = None


class LeadCreate(BaseModel):
    business_id: int
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    intent: Optional[str] = None
    notes: Optional[str] = None


class LeadOut(BaseModel):
    id: int
    business_id: int
    name: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    intent: Optional[str]
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalyticsOut(BaseModel):
    total_calls: int
    successful_calls: int
    transferred: int
    failed: int
    avg_duration_seconds: float
    appointments: int
    leads_captured: int
