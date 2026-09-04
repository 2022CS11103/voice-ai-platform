from __future__ import annotations

import io
import logging
import tempfile
from pathlib import Path
from typing import Optional

import edge_tts
import imageio_ffmpeg
from pydub import AudioSegment

from app.config import get_settings
from app.services.audio_codec import pcm16_8k_to_mulaw

logger = logging.getLogger(__name__)
settings = get_settings()

# Point pydub at the bundled ffmpeg binary (no system install needed)
AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()
AudioSegment.ffprobe = imageio_ffmpeg.get_ffmpeg_exe()


async def synthesize_mulaw(
    text: str,
    voice: Optional[str] = None,
) -> bytes:
    """
    Free Edge TTS (MP3) → 8kHz μ-law for Twilio Media Streams.
    Uses imageio-ffmpeg so no system ffmpeg install is required.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return b""
    if len(cleaned) > 500:
        cleaned = cleaned[:500] + "…"

    voice_name = _map_voice(voice or settings.tts_voice)

    try:
        mp3 = await _edge_mp3(cleaned, voice_name)
        if mp3:
            return _mp3_to_mulaw(mp3)
    except Exception:
        logger.exception("Edge TTS failed; trying local SAPI fallback")

    return await _sapi_mulaw(cleaned)


def _map_voice(name: str) -> str:
    mapping = {
        "alloy": "en-US-JennyNeural",
        "ash": "en-US-GuyNeural",
        "ballad": "en-US-AriaNeural",
        "coral": "en-US-JennyNeural",
        "echo": "en-US-ChristopherNeural",
        "sage": "en-US-JennyNeural",
        "shimmer": "en-US-AriaNeural",
        "verse": "en-US-GuyNeural",
    }
    if name in mapping:
        return mapping[name]
    if "Neural" in name or name.startswith("en-"):
        return name
    return settings.tts_voice


async def _edge_mp3(text: str, voice: str) -> bytes:
    communicate = edge_tts.Communicate(text, voice)
    audio = bytearray()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio.extend(chunk["data"])
    logger.info("Edge TTS mp3 bytes=%s", len(audio))
    return bytes(audio)


def _mp3_to_mulaw(mp3_bytes: bytes) -> bytes:
    segment = AudioSegment.from_file(io.BytesIO(mp3_bytes), format="mp3")
    segment = segment.set_frame_rate(8000).set_channels(1).set_sample_width(2)
    pcm = segment.raw_data
    return pcm16_8k_to_mulaw(pcm)


async def _sapi_mulaw(text: str) -> bytes:
    import asyncio
    import wave

    try:
        import pyttsx3
    except ImportError:
        logger.error("pyttsx3 not installed; cannot fallback TTS")
        return b""

    def _write_wav(path: str) -> None:
        engine = pyttsx3.init()
        engine.setProperty("rate", 175)
        engine.save_to_file(text, path)
        engine.runAndWait()

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = tmp.name

    try:
        await asyncio.to_thread(_write_wav, wav_path)
        with wave.open(wav_path, "rb") as wf:
            pcm = wf.readframes(wf.getnframes())
            rate = wf.getframerate()
            width = wf.getsampwidth()
            channels = wf.getnchannels()
        import audioop

        if channels == 2:
            pcm = audioop.tomono(pcm, width, 0.5, 0.5)
        if width != 2:
            pcm = audioop.lin2lin(pcm, width, 2)
            width = 2
        if rate != 8000:
            pcm, _ = audioop.ratecv(pcm, width, 1, rate, 8000, None)
        return pcm16_8k_to_mulaw(pcm)
    finally:
        Path(wav_path).unlink(missing_ok=True)
