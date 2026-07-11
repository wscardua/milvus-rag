"""Contrato query-and-citations: POST /query + feedback (retrieval + citações + auditoria)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.db.base import get_session
from app.db.models import FEEDBACK_RATINGS, QueryLog
from app.domain.retrieval import retriever
from app.schemas.query import (
    FeedbackRequest,
    QueryRequest,
    QueryResponse,
    RetrieveRequest,
    RetrieveResponse,
)
from app.services import eventlog

router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse)
def query(payload: QueryRequest, session: Session = Depends(get_session)):
    if not payload.question.strip():
        raise HTTPException(422, "Pergunta vazia.")
    top_k = payload.top_k or settings.retrieval_top_k
    try:
        result = retriever.answer_query(
            session, payload.question, payload.filters, top_k, payload.conversation_id
        )
    except retriever.ConversationNotFoundError:
        raise HTTPException(404, "Conversa não encontrada.")
    except Exception as exc:  # noqa: BLE001 — falha de índice/modelo → erro claro, sem resposta fabricada
        eventlog.log_event("ERROR", "retrieval", "query_failed", str(exc))
        raise HTTPException(502, f"Falha no retrieval/geração: {exc}")

    metrics = result.pop("metrics", {})
    conversation_id = result.pop("conversation_id", None)  # ADR-0016
    turn_index = result.pop("turn_index", None)
    log = QueryLog(
        question=payload.question,
        filters=payload.filters,
        top_k=top_k,
        insufficient_context=result["insufficient_context"],
        answer=result["answer"],
        citations=result["citations"],
        linked_flow=result["linked_flow"],
        conversation_id=conversation_id,
        turn_index=turn_index,
        **metrics,
    )
    session.add(log)
    session.commit()
    session.refresh(log)

    return {
        "query_id": str(log.id),
        "conversation_id": str(conversation_id) if conversation_id else None,
        "turn_index": turn_index,
        **result,
    }


@router.post("/retrieve", response_model=RetrieveResponse)
def retrieve(payload: RetrieveRequest, session: Session = Depends(get_session)):
    """Retrieval puro (sem geração) — trechos relevantes para o agente montar o prompt.

    Endpoint dedicado (ADR-0005/FEAT-MCP-001): não gera resposta nem grava `query_log`
    (não há feedback a ancorar). Consumido pela tool `retrieve_chunks` do MCP.
    """
    if not payload.question.strip():
        raise HTTPException(422, "Pergunta vazia.")
    top_k = payload.top_k or settings.retrieval_top_k
    try:
        result = retriever.retrieve_chunks(session, payload.question, payload.filters, top_k)
    except Exception as exc:  # noqa: BLE001 — falha de índice/modelo → erro claro
        eventlog.log_event("ERROR", "retrieval", "retrieve_failed", str(exc))
        raise HTTPException(502, f"Falha no retrieval: {exc}")
    result.pop("metrics", None)
    return result


@router.post("/query/{query_id}/feedback", status_code=204)
def submit_feedback(
    query_id: uuid.UUID,
    payload: FeedbackRequest,
    session: Session = Depends(get_session),
):
    """Registra o 'joinha' (👍/👎) na consulta para análise de qualidade (ADR-0011)."""
    log = session.get(QueryLog, query_id)
    if not log:
        raise HTTPException(404, "Consulta não encontrada.")
    log.rating = FEEDBACK_RATINGS[payload.rating]
    log.rating_at = datetime.now(timezone.utc)
    session.commit()
    return None
