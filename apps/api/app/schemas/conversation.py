"""Schemas do contrato conversations (ADR-0016, chat multi-turno)."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class ConversationCreate(BaseModel):
    title: str | None = None
    squad_id: uuid.UUID | None = None


class ConversationOut(BaseModel):
    id: str
    title: str | None
    squad_id: str | None
    created_at: datetime
    updated_at: datetime


class ConversationTurnOut(BaseModel):
    turn_index: int
    question: str
    answer: str | None
    citations: list[dict] | None
    linked_flow: list[dict] | None
    insufficient_context: bool
    created_at: datetime


class ConversationDetailOut(ConversationOut):
    turns: list[ConversationTurnOut]
