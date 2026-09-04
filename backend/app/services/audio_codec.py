from __future__ import annotations

import audioop
import io
import struct
import wave
from typing import List


def mulaw_chunks_to_wav_bytes(mulaw_payloads: List[bytes], sample_rate: int = 8000) -> bytes:
    """Twilio μ-law frames → mono 16-bit WAV (for Groq Whisper)."""
    mulaw = b"".join(mulaw_payloads)
    if not mulaw:
        return b""
    pcm = audioop.ulaw2lin(mulaw, 2)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    return buf.getvalue()


def pcm16_rms(pcm: bytes) -> float:
    if len(pcm) < 2:
        return 0.0
    try:
        return float(audioop.rms(pcm, 2))
    except Exception:
        return 0.0


def mulaw_frame_rms(mulaw_b64_decoded: bytes) -> float:
    if not mulaw_b64_decoded:
        return 0.0
    pcm = audioop.ulaw2lin(mulaw_b64_decoded, 2)
    return pcm16_rms(pcm)


def downsample_pcm16_24k_to_8k(pcm24: bytes) -> bytes:
    """Naive 3:1 downsample 24kHz → 8kHz mono PCM16."""
    if not pcm24:
        return b""
    # Prefer audioop ratecv when available
    try:
        converted, _ = audioop.ratecv(pcm24, 2, 1, 24000, 8000, None)
        return converted
    except Exception:
        samples = memoryview(pcm24).cast("h")
        out = [samples[i] for i in range(0, len(samples), 3)]
        return struct.pack(f"<{len(out)}h", *out)


def pcm16_8k_to_mulaw(pcm8: bytes) -> bytes:
    return audioop.lin2ulaw(pcm8, 2)
