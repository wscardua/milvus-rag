"""Chunking por janelas de palavras com overlap (default configurável, chunk < 2048 tokens)."""
from __future__ import annotations

from app.config import settings


def chunk_text(text: str, size: int | None = None, overlap: int | None = None) -> list[str]:
    size = size or settings.chunk_size_words
    overlap = overlap or settings.chunk_overlap_words
    words = text.split()
    if not words:
        return []
    step = max(1, size - overlap)
    chunks: list[str] = []
    i = 0
    while i < len(words):
        chunks.append(" ".join(words[i : i + size]))
        if i + size >= len(words):
            break
        i += step
    return chunks
