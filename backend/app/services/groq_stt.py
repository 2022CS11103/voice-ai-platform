from __future__ import annotations

import io
import logging
from typing import Optional

from groq import AsyncGroq

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def transcribe_wav(wav_bytes: bytes, language: str = "en") -> str:
    """Transcribe WAV audio with Groq Whisper (free tier)."""
    if not wav_bytes:
        return ""
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")

    client = AsyncGroq(api_key=settings.groq_api_key)
    file_obj = io.BytesIO(wav_bytes)
    file_obj.name = "utterance.wav"

    result = await client.audio.transcriptions.create(
        file=("utterance.wav", file_obj, "audio/wav"),
        model=settings.groq_stt_model,
        language=language,
        response_format="text",
    )
    # SDK may return str or object with .text
    if isinstance(result, str):
        text = result
    else:
        text = getattr(result, "text", "") or str(result)
    text = (text or "").strip()
    logger.info("STT: %s", text[:120])
    return text
