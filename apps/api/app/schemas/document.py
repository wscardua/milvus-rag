"""Schemas dos contratos upload-and-metadata (ADR-0007) e document-links (ADR-0008)."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class LinkIn(BaseModel):
    target_document_id: uuid.UUID
    link_type: str  # esclarece | complementa | precede | substitui
    ordinal: int | None = None


class LinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    source_document_id: uuid.UUID
    target_document_id: uuid.UUID
    link_type: str
    ordinal: int | None = None


class DocumentUpdate(BaseModel):
    """PATCH /documents/{id} — overrides de classificação (ADR-0007) + metadados de entrega (ADR-0014)."""
    title: str | None = Field(default=None, max_length=500)
    category_id: uuid.UUID | None = None
    subcategory_id: uuid.UUID | None = None
    summary: str | None = None
    # Ciclo de entrega (ADR-0014) — entrada do usuário, não altera classification_source
    delivery_phase: str | None = Field(default=None, max_length=60)
    valid_until: date | None = None


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    delivery_process_id: uuid.UUID
    squad_id: uuid.UUID | None = None
    title: str | None = None
    author: str | None = None
    tags: list[str] = []
    doc_type: str | None = None
    delivery_phase: str | None = None
    valid_until: date | None = None
    original_filename: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    category_id: uuid.UUID | None = None
    subcategory_id: uuid.UUID | None = None
    summary: str | None = None
    classification_source: str | None = None
    ingested_at: datetime | None = None
    status: str  # do ingestion_job mais recente
    created_at: datetime
    updated_at: datetime
