"""Aplicação FastAPI — domínio/fonte da verdade da POC de RAG (ADR-0003)."""
from __future__ import annotations

from fastapi import FastAPI

from app.api import documents, links, organization, query, system

app = FastAPI(title="Milvus RAG API", version="0.1.0")

app.include_router(organization.router)
app.include_router(documents.router)
app.include_router(links.router)
app.include_router(query.router)
app.include_router(system.router)  # /health detalhado + /logs (ADR-0011)
