"""Cliente OpenAI-compatível do LM Studio (embeddings + chat). base_url por env (ADR-0002/0006)."""
from __future__ import annotations

from openai import OpenAI

from app.config import settings

client = OpenAI(base_url=settings.lm_studio_base_url, api_key=settings.lm_studio_api_key)
