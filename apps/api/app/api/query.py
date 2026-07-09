"""Contrato query-and-citations: POST /query (retrieval + expansão + geração com citações)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.db.base import get_session
from app.domain.retrieval import retriever
from app.schemas.query import QueryRequest, QueryResponse

router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse)
def query(payload: QueryRequest, session: Session = Depends(get_session)):
    if not payload.question.strip():
        raise HTTPException(422, "Pergunta vazia.")
    top_k = payload.top_k or settings.retrieval_top_k
    try:
        return retriever.answer_query(session, payload.question, payload.filters, top_k)
    except Exception as exc:  # noqa: BLE001 — falha de índice/modelo → erro claro, sem resposta fabricada
        raise HTTPException(502, f"Falha no retrieval/geração: {exc}")
