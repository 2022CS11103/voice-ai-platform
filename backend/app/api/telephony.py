from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel, Field
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client
from twilio.twiml.voice_response import Connect, Stream, VoiceResponse

from app.config import get_settings, refresh_settings
from app.db.models import User
from app.services.auth import get_current_user
from app.services.voice_bridge import VoiceRealtimeBridge

router = APIRouter(tags=["telephony"])


def _public_host(request: Request | None = None) -> str:
    """Prefer PUBLIC_BASE_URL host so local ngrok tunnels work behind proxies."""
    get_settings.cache_clear()
    settings = get_settings()
    raw = (settings.public_base_url or "").strip()
    if raw:
        parsed = urlparse(raw)
        if parsed.hostname:
            return parsed.netloc
    if request is not None:
        return request.headers.get("host") or request.url.netloc
    raise RuntimeError("PUBLIC_BASE_URL is not set")


def _public_https_base() -> str:
    get_settings.cache_clear()
    settings = get_settings()
    base = (settings.public_base_url or "").strip().rstrip("/")
    if not base.startswith("https://"):
        raise HTTPException(
            status_code=400,
            detail="PUBLIC_BASE_URL must be your https ngrok URL for Twilio outbound calls.",
        )
    return base


def _normalize_e164(raw: str) -> str:
    cleaned = re.sub(r"[^\d+]", "", (raw or "").strip())
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    if cleaned.startswith("+"):
        return cleaned
    # India local 10-digit → +91
    if len(cleaned) == 10 and cleaned[0] in "6789":
        return "+91" + cleaned
    if cleaned.startswith("91") and len(cleaned) == 12:
        return "+" + cleaned
    if cleaned.startswith("1") and len(cleaned) == 11:
        return "+" + cleaned
    raise HTTPException(
        status_code=400,
        detail="Use full international format, e.g. +918318762518",
    )


def _twilio_client() -> Client:
    """Build Twilio client; tolerate common SID/token swap in .env."""
    settings = refresh_settings()
    sid = (settings.twilio_account_sid or "").strip()
    token = (settings.twilio_auth_token or "").strip()
    from_number = (settings.twilio_phone_number or "").strip()

    if not settings.twilio_ready:
        raise HTTPException(
            status_code=400,
            detail=(
                "Twilio not configured. In backend/.env set TWILIO_ACCOUNT_SID (ACxxx), "
                "TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER — then restart uvicorn."
            ),
        )

    if sid.startswith("SK") and token.startswith("AC"):
        raise HTTPException(
            status_code=400,
            detail=(
                "Your Twilio credentials look swapped. Set TWILIO_ACCOUNT_SID=ACxxx "
                "and TWILIO_AUTH_TOKEN to the Auth Token from Twilio Console."
            ),
        )

    return Client(sid, token)


def _twiml_connect(host: str, agent_id: Optional[str] = None) -> str:
    response = VoiceResponse()
    response.pause(length=1)
    connect = Connect()
    stream_url = f"wss://{host}/telephony/stream"
    stream = Stream(url=stream_url)
    if agent_id:
        stream.parameter(name="agent_id", value=str(agent_id))
    connect.append(stream)
    response.append(connect)
    return str(response)


@router.get("/telephony/debug")
async def telephony_debug(request: Request):
    get_settings.cache_clear()
    settings = get_settings()
    host = _public_host(request)
    return {
        "public_base_url": settings.public_base_url,
        "computed_host": host,
        "stream_url": f"wss://{host}/telephony/stream",
        "webhook_url": f"https://{host}/telephony/incoming",
        "from_number": settings.twilio_phone_number,
        "request_host": request.headers.get("host"),
    }


@router.api_route("/telephony/incoming", methods=["GET", "POST"])
async def incoming_call(request: Request):
    """Twilio webhook — return TwiML that opens a Media Stream to our WebSocket."""
    host = _public_host(request)
    agent_id = request.query_params.get("agent_id")
    xml = _twiml_connect(host, agent_id)
    stream_url = f"wss://{host}/telephony/stream"
    if "localhost" in stream_url or "127.0.0.1" in stream_url:
        return PlainTextResponse(
            content=(
                f"Misconfigured PUBLIC_BASE_URL. Got stream_url={stream_url}. "
                f"Set PUBLIC_BASE_URL to your ngrok https URL and restart backend."
            ),
            status_code=500,
        )
    return HTMLResponse(content=xml, media_type="application/xml")


class OutboundCallIn(BaseModel):
    to: str = Field(..., description="Your phone in E.164, e.g. +918318762518")
    agent_id: Optional[int] = None


class OutboundCallOut(BaseModel):
    ok: bool
    call_sid: str
    to: str
    from_number: str
    message: str


@router.post("/api/telephony/call-me", response_model=OutboundCallOut)
async def call_me(
    payload: OutboundCallIn,
    user: User = Depends(get_current_user),
):
    """
    Place an outbound call TO your phone so you can test the AI without dialing in.
    Trial Twilio accounts can only call Verified Caller IDs — verify +91… in Console first.
    """
    _ = user
    settings = get_settings()
    to = _normalize_e164(payload.to)
    from_number = (settings.twilio_phone_number or "").strip()
    base = _public_https_base()
    twiml_url = f"{base}/telephony/incoming"
    if payload.agent_id:
        twiml_url += f"?agent_id={payload.agent_id}"

    client = _twilio_client()
    try:
        call = client.calls.create(
            to=to,
            from_=from_number,
            url=twiml_url,
            method="POST",
        )
    except TwilioRestException as exc:
        hint = ""
        msg = (exc.msg or str(exc)).lower()
        if "unverified" in msg or "not a valid" in msg or exc.code in {21219, 21214}:
            hint = (
                " Twilio trial: verify your number at "
                "https://console.twilio.com/us1/develop/phone-numbers/manage/verified"
                f" → add {to}, then retry."
            )
        if "authenticate" in msg or exc.status == 401:
            hint = (
                " Check TWILIO_ACCOUNT_SID (ACxxx) and TWILIO_AUTH_TOKEN "
                "from Twilio Console → Account → API keys & tokens."
            )
        raise HTTPException(
            status_code=400,
            detail=f"Twilio error: {exc.msg or exc}{hint}",
        ) from exc

    return OutboundCallOut(
        ok=True,
        call_sid=call.sid,
        to=to,
        from_number=from_number,
        message=f"Calling {to} now — pick up to talk to your AI agent.",
    )


@router.websocket("/telephony/stream")
async def media_stream(websocket: WebSocket):
    agent_id = None
    if websocket.query_params.get("agent_id"):
        try:
            agent_id = int(websocket.query_params["agent_id"])
        except ValueError:
            agent_id = None

    bridge = VoiceRealtimeBridge(websocket, agent_id=agent_id)
    await bridge.start()
    await bridge.run()
