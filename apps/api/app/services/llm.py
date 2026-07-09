"""Geração de texto (chat) via LM Studio. Usado na classificação e na resposta com citações."""
from __future__ import annotations

from app.config import settings
from app.services.lmstudio import client


def chat(messages: list[dict], max_tokens: int = 512, temperature: float = 0.2) -> str:
    resp = client.chat.completions.create(
        model=settings.chat_model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return (resp.choices[0].message.content or "").strip()
