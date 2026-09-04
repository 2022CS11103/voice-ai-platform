from __future__ import annotations

import asyncio
import base64
import contextlib
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect
from sqlalchemy import select

from app.config import get_settings
from app.db.models import Agent, Business, Call, Message
from app.db.session import AsyncSessionLocal
from app.services.audio_codec import mulaw_chunks_to_wav_bytes, mulaw_frame_rms
from app.services.groq_llm import run_agent_turn
from app.services.groq_stt import transcribe_wav
from app.services.prompt import build_system_prompt
from app.services.tts import synthesize_mulaw
from app.tools import ToolExecutor

logger = logging.getLogger(__name__)
settings = get_settings()

# Simple energy VAD tuned for Twilio 20ms μ-law frames (~160 bytes)
SPEECH_RMS_THRESHOLD = 250
SILENCE_FRAMES_END = 18  # ~360ms of silence after speech → end of turn
MIN_SPEECH_FRAMES = 8  # ignore tiny blips
MAX_UTTERANCE_FRAMES = 400  # ~8s cap
TWILIO_CHUNK = 160  # bytes of μ-law per media message (~20ms)


class VoiceRealtimeBridge:
    """Twilio Media Streams ↔ Groq Whisper + Groq LLM + Edge TTS."""

    def __init__(self, websocket: WebSocket, agent_id: Optional[int] = None) -> None:
        self.websocket = websocket
        self.requested_agent_id = agent_id
        self.stream_sid: Optional[str] = None
        self.call_sid: Optional[str] = None
        self.caller_number: Optional[str] = None
        self.agent: Optional[Agent] = None
        self.business: Optional[Business] = None
        self.call_row: Optional[Call] = None
        self.tools: Optional[ToolExecutor] = None
        self.system_prompt: str = ""
        self.history: list[dict] = []
        self._busy = False
        self._closed = False

        self._utterance: list[bytes] = []
        self._speech_frames = 0
        self._silence_frames = 0
        self._in_speech = False

    async def start(self) -> None:
        subprotocol_header = self.websocket.headers.get("sec-websocket-protocol")
        subprotocol = None
        if subprotocol_header:
            subprotocol = subprotocol_header.split(",", 1)[0].strip()
        await self.websocket.accept(subprotocol=subprotocol)

        if not settings.groq_api_key:
            await self.websocket.close(code=1011)
            raise RuntimeError("GROQ_API_KEY is not configured")

        logger.info("Groq voice bridge ready")

    async def run(self) -> None:
        try:
            await self._receive_from_twilio()
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        self._closed = True
        await self._finalize_call()
        with contextlib.suppress(RuntimeError):
            await self.websocket.close()

    async def _load_agent_context(self) -> None:
        async with AsyncSessionLocal() as db:
            agent: Optional[Agent] = None
            if self.requested_agent_id:
                result = await db.execute(select(Agent).where(Agent.id == self.requested_agent_id))
                agent = result.scalar_one_or_none()
            if agent is None:
                result = await db.execute(
                    select(Agent).where(Agent.status == "active").order_by(Agent.id.asc())
                )
                agents = list(result.scalars().all())
                agent = agents[0] if agents else None
            if not agent:
                raise RuntimeError("No active agent configured")

            biz_result = await db.execute(select(Business).where(Business.id == agent.business_id))
            business = biz_result.scalar_one()

            call = Call(
                agent_id=agent.id,
                caller_number=self.caller_number,
                twilio_call_sid=self.call_sid,
                status="in_progress",
            )
            db.add(call)
            await db.commit()
            await db.refresh(call)

            self.agent = agent
            self.business = business
            self.call_row = call
            self.tools = ToolExecutor(agent.id, business.id, self.caller_number)
            self.system_prompt = agent.system_prompt or build_system_prompt(agent, business)
            self.system_prompt += (
                "\n\nYou are on a live phone call. Keep answers short (1-3 sentences). "
                "Always respond to what the caller just said, then ask exactly one follow-up "
                "question that fits their reply (next missing booking detail or clarification). "
                "Use tools for facts, availability, guests, and booking."
            )

    async def _receive_from_twilio(self) -> None:
        try:
            async for message in self.websocket.iter_text():
                if self._closed:
                    break
                import json

                data = json.loads(message)
                event = data.get("event")

                if event == "start":
                    start = data.get("start", {})
                    self.stream_sid = start.get("streamSid")
                    self.call_sid = start.get("callSid")
                    custom = start.get("customParameters") or {}
                    agent_param = custom.get("agent_id")
                    if agent_param and not self.requested_agent_id:
                        with contextlib.suppress(ValueError):
                            self.requested_agent_id = int(agent_param)
                    self.caller_number = start.get("from") or self.caller_number
                    logger.info("Stream started sid=%s", self.stream_sid)
                    await self._load_agent_context()
                    greeting = (
                        (self.agent.greeting if self.agent else None)
                        or "Hi! Thanks for calling. How can I help you today?"
                    )
                    await self._speak(greeting)
                    await self._save_message("ai", greeting)
                    self.history.append({"role": "assistant", "content": greeting})

                elif event == "media":
                    if self._busy:
                        continue
                    payload = data.get("media", {}).get("payload")
                    if not payload:
                        continue
                    frame = base64.b64decode(payload)
                    await self._handle_audio_frame(frame)

                elif event == "stop":
                    logger.info("Twilio stream stopped")
                    break
        except WebSocketDisconnect:
            logger.info("Twilio WebSocket disconnected")

    async def _handle_audio_frame(self, frame: bytes) -> None:
        rms = mulaw_frame_rms(frame)
        is_speech = rms >= SPEECH_RMS_THRESHOLD

        if is_speech:
            self._in_speech = True
            self._silence_frames = 0
            self._speech_frames += 1
            self._utterance.append(frame)
        elif self._in_speech:
            self._utterance.append(frame)
            self._silence_frames += 1
            if self._silence_frames >= SILENCE_FRAMES_END and self._speech_frames >= MIN_SPEECH_FRAMES:
                await self._flush_utterance()
        # ignore silence before speech

        if len(self._utterance) >= MAX_UTTERANCE_FRAMES:
            await self._flush_utterance()

    async def _flush_utterance(self) -> None:
        frames = self._utterance
        self._utterance = []
        speech_frames = self._speech_frames
        self._speech_frames = 0
        self._silence_frames = 0
        self._in_speech = False

        if speech_frames < MIN_SPEECH_FRAMES or not frames:
            return
        if self._busy:
            return

        self._busy = True
        try:
            wav = mulaw_chunks_to_wav_bytes(frames)
            user_text = await transcribe_wav(wav)
            if not user_text or len(user_text) < 2:
                return

            await self._save_message("customer", user_text)
            assert self.tools is not None

            reply = await run_agent_turn(
                system_prompt=self.system_prompt,
                history=self.history,
                user_text=user_text,
                tools=self.tools,
            )
            self.history.append({"role": "user", "content": user_text})
            self.history.append({"role": "assistant", "content": reply})
            # Keep history bounded
            if len(self.history) > 20:
                self.history = self.history[-20:]

            await self._save_message("ai", reply)
            await self._speak(reply)
        except Exception:
            logger.exception("Failed to process utterance")
            with contextlib.suppress(Exception):
                await self._speak("Sorry, I had trouble with that. Could you say it again?")
        finally:
            self._busy = False

    async def _speak(self, text: str) -> None:
        if not self.stream_sid or self._closed:
            return
        voice = self.agent.voice if self.agent else settings.tts_voice
        mulaw = await synthesize_mulaw(text, voice=voice)
        if not mulaw:
            logger.warning("No TTS audio for: %s", text[:80])
            return

        # Clear any queued caller audio playback
        await self.websocket.send_json({"event": "clear", "streamSid": self.stream_sid})

        # Stream in ~20ms chunks
        for i in range(0, len(mulaw), TWILIO_CHUNK):
            if self._closed:
                break
            chunk = mulaw[i : i + TWILIO_CHUNK]
            if len(chunk) < TWILIO_CHUNK:
                chunk = chunk + (b"\xff" * (TWILIO_CHUNK - len(chunk)))
            await self.websocket.send_json(
                {
                    "event": "media",
                    "streamSid": self.stream_sid,
                    "media": {"payload": base64.b64encode(chunk).decode("utf-8")},
                }
            )
            await asyncio.sleep(0.02)

        await self.websocket.send_json(
            {
                "event": "mark",
                "streamSid": self.stream_sid,
                "mark": {"name": "responseEnd"},
            }
        )

    async def _save_message(self, role: str, content: str) -> None:
        if not self.call_row:
            return
        async with AsyncSessionLocal() as db:
            db.add(Message(call_id=self.call_row.id, role=role, content=content))
            await db.commit()

    async def _finalize_call(self) -> None:
        if not self.call_row:
            return
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Call).where(Call.id == self.call_row.id))
            call = result.scalar_one_or_none()
            if not call:
                return
            call.ended_at = datetime.now(timezone.utc)
            if call.started_at:
                started = call.started_at
                if started.tzinfo is None:
                    started = started.replace(tzinfo=timezone.utc)
                call.duration_seconds = max(int((call.ended_at - started).total_seconds()), 0)
            call.status = "completed"
            if self.tools and self.tools.last_outcome:
                call.outcome = self.tools.last_outcome
                call.intent = self.tools.last_outcome
            else:
                call.outcome = call.outcome or "Completed"

            msg_result = await db.execute(
                select(Message).where(Message.call_id == call.id).order_by(Message.id.asc())
            )
            messages = list(msg_result.scalars().all())
            if messages and not call.summary:
                customer_bits = [m.content for m in messages if m.role == "customer"][:3]
                call.summary = (
                    " | ".join(customer_bits) if customer_bits else "Voice conversation completed."
                )
                call.sentiment = "Positive"
            await db.commit()
