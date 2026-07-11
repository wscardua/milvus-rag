"""Schemas do contrato query-and-citations (ADR-0008/0011/0016)."""
from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str
    # squad, delivery_process, category, doc_type (str); delivery_phase (str, ADR-0015);
    # tags (list[str], ADR-0015 — semântica OR)
    filters: dict | None = None
    top_k: int | None = None
    conversation_id: uuid.UUID | None = None  # ADR-0016 — ausente = consulta stateless


class Citation(BaseModel):
    document_id: str
    chunk_id: str
    snippet: str
    score: float


class LinkedFlow(BaseModel):
    source_document_id: str
    target_document_id: str
    link_type: str
    included: bool


class QueryResponse(BaseModel):
    query_id: str  # id do query_log — âncora do feedback (ADR-0011)
    answer: str | None
    insufficient_context: bool
    citations: list[Citation]
    linked_flow: list[LinkedFlow]
    conversation_id: str | None = None  # ADR-0016 — ecoado quando a requisição informou
    turn_index: int | None = None


class FeedbackRequest(BaseModel):
    rating: Literal["up", "down"]  # 👍 / 👎


# --- Retrieval puro (sem geração) — FEAT-MCP-001 / ADR-0005 ---
class RetrieveRequest(BaseModel):
    question: str
    filters: dict | None = None  # mesmos filtros de /query (inclui delivery_phase/tags, ADR-0015)
    top_k: int | None = None


class RetrievedChunk(BaseModel):
    document_id: str
    chunk_id: str
    ordinal: int
    text: str
    score: float


class RetrieveResponse(BaseModel):
    insufficient_context: bool
    chunks: list[RetrievedChunk]
