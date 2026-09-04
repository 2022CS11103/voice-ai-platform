import asyncio
import aiohttp
from edge_tts.communicate import (
    WSS_HEADERS,
    WSS_URL,
    _SSL_CTX,
    connect_id,
    date_to_string,
    get_headers_and_data,
    mkssml,
    ssml_headers_plus_data,
)
from edge_tts.constants import SEC_MS_GEC_VERSION
from edge_tts.data_classes import TTSConfig
from edge_tts.drm import DRM

FORMATS = [
    "raw-8khz-8bit-mono-mulaw",
    "raw-24khz-16bit-mono-pcm",
    "riff-8khz-8bit-mono-mulaw",
    "riff-24khz-16bit-mono-pcm",
    "audio-24khz-48kbitrate-mono-mp3",
]


async def try_fmt(fmt: str) -> None:
    tts_config = TTSConfig("en-US-JennyNeural", "+0%", "+0%", "+0Hz", "SentenceBoundary")
    audio = bytearray()
    ctypes: set = set()
    async with aiohttp.ClientSession(
        trust_env=True, timeout=aiohttp.ClientTimeout(total=30)
    ) as session:
        url = (
            f"{WSS_URL}&ConnectionId={connect_id()}"
            f"&Sec-MS-GEC={DRM.generate_sec_ms_gec()}"
            f"&Sec-MS-GEC-Version={SEC_MS_GEC_VERSION}"
        )
        async with session.ws_connect(
            url,
            compress=15,
            headers=DRM.headers_with_muid(WSS_HEADERS),
            ssl=_SSL_CTX,
        ) as ws:
            cfg = (
                f"X-Timestamp:{date_to_string()}\r\n"
                "Content-Type:application/json; charset=utf-8\r\n"
                "Path:speech.config\r\n\r\n"
                '{"context":{"synthesis":{"audio":{"metadataoptions":{'
                '"sentenceBoundaryEnabled":"true","wordBoundaryEnabled":"false"'
                "},"
                f'"outputFormat":"{fmt}"'
                "}}}}\r\n"
            )
            await ws.send_str(cfg)
            await ws.send_str(
                ssml_headers_plus_data(
                    connect_id(),
                    date_to_string(),
                    mkssml(tts_config, b"Hello there"),
                )
            )
            async for received in ws:
                if received.type == aiohttp.WSMsgType.TEXT:
                    enc = received.data.encode()
                    parameters, _ = get_headers_and_data(enc, enc.find(b"\r\n\r\n"))
                    if parameters.get(b"Path") == b"turn.end":
                        break
                elif received.type == aiohttp.WSMsgType.BINARY and len(received.data) >= 2:
                    hl = int.from_bytes(received.data[:2], "big")
                    parameters, data = get_headers_and_data(received.data, hl)
                    ctypes.add(parameters.get(b"Content-Type"))
                    if data:
                        audio.extend(data)
    print(fmt, "bytes", len(audio), "ctypes", ctypes, "head", bytes(audio[:8]))


async def main() -> None:
    for fmt in FORMATS:
        try:
            await try_fmt(fmt)
        except Exception as exc:  # noqa: BLE001
            print(fmt, "ERR", exc)


if __name__ == "__main__":
    asyncio.run(main())
