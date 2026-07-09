"""Schemas do contrato query-and-citations (ADR-0008)."""
from __future__ import annotations

from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str
    filters: dict | None = None  # squad, delivery_process, category, doc_type
    top_k: int | None = None


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
    answer: str | None
    insufficient_context: bool
    citations: list[Citation]
    linked_flow: list[LinkedFlow]
