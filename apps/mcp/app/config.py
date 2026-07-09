"""Configuração do servidor MCP (ADR-0006): tudo por env, nada hardcoded.

O MCP é um cliente HTTP leve da API FastAPI (ADR-0005) — só precisa saber onde a
API está e o transporte a expor.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # API FastAPI (fonte da verdade) — porta 8001 no dev local (Django usa a 8000)
    api_base_url: str = "http://localhost:8001"
    api_timeout_seconds: float = 60.0

    # Transporte MCP: stdio (default, integração local) ou http/sse (evolução)
    mcp_transport: str = "stdio"


settings = Settings()
