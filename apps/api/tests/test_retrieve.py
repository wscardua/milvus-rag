"""Testes do endpoint POST /retrieve — retrieval puro, sem geração (FEAT-MCP-001, ADR-0005)."""
from __future__ import annotations

import pytest


def test_empty_question_422(client):
    assert client.post("/retrieve", json={"question": "   "}).status_code == 422


def test_retrieve_returns_chunks_without_generation(client):
    resp = client.post("/retrieve", json={"question": "o que há no acervo?", "top_k": 3})
    if resp.status_code == 502:
        pytest.skip("LM Studio indisponível para o embedding da pergunta.")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # shape do contrato: sem 'answer'/'citations' (é retrieval puro), com chunks + score
    assert set(body.keys()) == {"insufficient_context", "chunks"}
    assert isinstance(body["insufficient_context"], bool)
    for ch in body["chunks"]:
        assert set(ch.keys()) == {"document_id", "chunk_id", "ordinal", "text", "score"}
        assert isinstance(ch["score"], (int, float))


def test_retrieve_does_not_write_query_log(client):
    """/retrieve é um primitivo: não deve criar linha em query_log (não há feedback a ancorar)."""
    from app.db.base import SessionLocal
    from app.db.models import QueryLog

    session = SessionLocal()
    before = session.query(QueryLog).count()
    session.close()

    resp = client.post("/retrieve", json={"question": "consulta de verificação de log", "top_k": 2})
    if resp.status_code == 502:
        pytest.skip("LM Studio indisponível para o embedding da pergunta.")
    assert resp.status_code == 200, resp.text

    session = SessionLocal()
    after = session.query(QueryLog).count()
    session.close()
    assert after == before  # /retrieve não grava query_log
