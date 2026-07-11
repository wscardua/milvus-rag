"""Contrato conversations: POST/GET /conversations, GET /conversations/{id} (ADR-0016)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.base import get_session
from app.db.models import Conversation, QueryLog
from app.schemas.conversation import ConversationCreate, ConversationDetailOut, ConversationOut

router = APIRouter(tags=["conversations"])


def _to_out(c: Conversation) -> dict:
    return {
        "id": str(c.id),
        "title": c.title,
        "squad_id": str(c.squad_id) if c.squad_id else None,
        "created_at": c.created_at,
        "updated_at": c.updated_at,
    }


@router.post("/conversations", response_model=ConversationOut)
def create_conversation(payload: ConversationCreate, session: Session = Depends(get_session)):
    conv = Conversation(title=payload.title, squad_id=payload.squad_id)
    session.add(conv)
    session.commit()
    session.refresh(conv)
    return _to_out(conv)


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(
    response: Response,
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_session),
):
    stmt = select(Conversation)
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    response.headers["X-Total-Count"] = str(total)
    convs = session.scalars(
        stmt.order_by(Conversation.updated_at.desc()).limit(min(limit, 200)).offset(offset)
    ).all()
    return [_to_out(c) for c in convs]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailOut)
def get_conversation(conversation_id: uuid.UUID, session: Session = Depends(get_session)):
    conv = session.get(Conversation, conversation_id)
    if conv is None:
        raise HTTPException(404, "Conversa não encontrada.")
    turns = session.scalars(
        select(QueryLog)
        .where(QueryLog.conversation_id == conversation_id)
        .order_by(QueryLog.turn_index)
    ).all()
    out = _to_out(conv)
    out["turns"] = [
        {
            "turn_index": t.turn_index,
            "question": t.question,
            "answer": t.answer,
            "citations": t.citations,
            "linked_flow": t.linked_flow,
            "insufficient_context": t.insufficient_context,
            "created_at": t.created_at,
        }
        for t in turns
    ]
    return out
