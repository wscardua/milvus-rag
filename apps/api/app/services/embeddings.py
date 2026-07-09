"""Geração de embeddings via LM Studio (`embeddinggemma-300m`, 768, COSINE)."""
from __future__ import annotations

from app.config import settings
from app.services.lmstudio import client


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embeddings em lote (uma chamada). Mantém a ordem da entrada."""
    if not texts:
        return []
    resp = client.embeddings.create(model=settings.embedding_model, input=texts)
    return [item.embedding for item in resp.data]


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
