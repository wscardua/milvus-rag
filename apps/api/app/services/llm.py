"""Geração de texto (chat) via LM Studio. Usado na classificação e na resposta com citações."""
from __future__ import annotations

from app.config import settings
from app.services.lmstudio import client


def chat(
    messages: list[dict],
    max_tokens: int = 512,
    temperature: float = 0.2,
    model: str | None = None,
) -> str:
    """`model` permite override (ex.: `condensation_model`, ADR-0017); default = `chat_model`."""
    resp = client.chat.completions.create(
        model=model or settings.chat_model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return (resp.choices[0].message.content or "").strip()
