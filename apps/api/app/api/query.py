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
from app.schemas.query import FeedbackRequest, QueryRequest, QueryResponse
from app.services import eventlog

router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse)
def query(payload: QueryRequest, session: Session = Depends(get_session)):
    if not payload.question.strip():
        raise HTTPException(422, "Pergunta vazia.")
    top_k = payload.top_k or settings.retrieval_top_k
    try:
        result = retriever.answer_query(session, payload.question, payload.filters, top_k)
    except Exception as exc:  # noqa: BLE001 — falha de índice/modelo → erro claro, sem resposta fabricada
        eventlog.log_event("ERROR", "retrieval", "query_failed", str(exc))
        raise HTTPException(502, f"Falha no retrieval/geração: {exc}")

    metrics = result.pop("metrics", {})
    log = QueryLog(
        question=payload.question,
        filters=payload.filters,
        top_k=top_k,
        insufficient_context=result["insufficient_context"],
        answer=result["answer"],
        citations=result["citations"],
        linked_flow=result["linked_flow"],
        **metrics,
    )
    session.add(log)
    session.commit()
    session.refresh(log)

    return {"query_id": str(log.id), **result}


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
