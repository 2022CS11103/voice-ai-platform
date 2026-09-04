from __future__ import annotations

import hashlib
import math
import re
from typing import Iterable, List

from app.config import get_settings

settings = get_settings()

EMBED_DIM = 384
# Pad to 1536 so existing pgvector / schema stays compatible
STORE_DIM = 1536


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 120) -> List[str]:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if not cleaned:
        return []
    chunks: List[str] = []
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + chunk_size)
        chunks.append(cleaned[start:end])
        if end == len(cleaned):
            break
        start = max(0, end - overlap)
    return chunks


def _local_embed(text: str) -> List[float]:
    """Deterministic bag-of-tokens embedding (no external API). Good enough for MVP RAG."""
    vec = [0.0] * EMBED_DIM
    tokens = re.findall(r"[a-z0-9$]+", text.lower())
    if not tokens:
        return vec
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:2], "little") % EMBED_DIM
        sign = 1.0 if digest[2] % 2 == 0 else -1.0
        weight = 1.0 + (digest[3] / 255.0)
        vec[idx] += sign * weight
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


async def embed_texts(texts: Iterable[str]) -> List[List[float]]:
    items = [t for t in texts if t and t.strip()]
    out: List[List[float]] = []
    for t in items:
        vec = _local_embed(t)
        if len(vec) < STORE_DIM:
            vec = vec + [0.0] * (STORE_DIM - len(vec))
        out.append(vec[:STORE_DIM])
    return out


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
