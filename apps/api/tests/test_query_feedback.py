"""Testes de query_log + feedback 👍/👎 (ADR-0011)."""
from __future__ import annotations

import uuid

import pytest

from app.db.base import SessionLocal
from app.db.models import QueryLog


def _run_query(client) -> dict:
    resp = client.post("/query", json={"question": "o que há no acervo?", "top_k": 3})
    if resp.status_code == 502:
        pytest.skip("LM Studio indisponível para o retrieval/geração.")
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_query_returns_id_and_persists_metrics(client):
    body = _run_query(client)
    assert "query_id" in body
    qid = body["query_id"]

    session = SessionLocal()
    row = session.get(QueryLog, uuid.UUID(qid))
    assert row is not None
    assert row.top_k == 3
    assert row.embedding_model  # snapshot dos modelos/params (tuning)
    assert row.chat_model
    assert row.latency_ms is not None and row.latency_ms >= 0
    assert row.rating is None  # ainda sem voto
    session.close()


def test_feedback_up_sets_rating(client):
    qid = _run_query(client)["query_id"]
    assert client.post(f"/query/{qid}/feedback", json={"rating": "up"}).status_code == 204

    session = SessionLocal()
    row = session.get(QueryLog, uuid.UUID(qid))
    assert row.rating == 1 and row.rating_at is not None
    session.close()


def test_feedback_invalid_rating_422(client):
    qid = _run_query(client)["query_id"]
    assert client.post(f"/query/{qid}/feedback", json={"rating": "meh"}).status_code == 422


def test_feedback_unknown_query_404(client):
    resp = client.post(f"/query/{uuid.uuid4()}/feedback", json={"rating": "up"})
    assert resp.status_code == 404


def test_empty_question_422(client):
    assert client.post("/query", json={"question": "   "}).status_code == 422
