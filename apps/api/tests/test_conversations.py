"""WORK-012: chat multi-turno (ADR-0016/ADR-0017).

Unitário (sem LM Studio): _truncate_words, _condense_question (com llm.chat mockado),
_fetch_recent_questions. Integração via TestClient contra o stack real (Postgres);
turnos completos de /query dependem de LM Studio real (pulam se indisponível, mesmo
padrão de test_query_feedback.py).
"""
from __future__ import annotations

import uuid

import pytest

from app.db.base import SessionLocal
from app.db.models import Conversation, QueryLog
from app.domain.retrieval import retriever
from app.domain.retrieval.retriever import _condense_question, _fetch_recent_questions, _truncate_words


# --- Unitário ---

def test_truncate_words_under_budget_is_noop():
    text = "uma frase curta"
    assert _truncate_words(text, 10) == text


def test_truncate_words_over_budget_cuts_by_word_count():
    text = " ".join(f"palavra{i}" for i in range(10))
    out = _truncate_words(text, 3)
    assert out == "palavra0 palavra1 palavra2"


def test_condense_question_without_history_returns_original():
    assert _condense_question([], "e quem é o responsável?") == "e quem é o responsável?"


def test_condense_question_uses_only_previous_questions_not_answers(monkeypatch):
    """A chamada de condensação recebe só perguntas anteriores (ADR-0017) — nunca respostas."""
    captured = {}

    def fake_chat(messages, max_tokens=512, temperature=0.2, model=None):
        captured["messages"] = messages
        captured["model"] = model
        return "Quem é o responsável pela homologação do contrato X?"

    monkeypatch.setattr(retriever.llm, "chat", fake_chat)
    prev_questions = ["Qual o status do contrato X?"]
    out = _condense_question(prev_questions, "e quem é o responsável por isso?")

    assert out == "Quem é o responsável pela homologação do contrato X?"
    user_content = captured["messages"][-1]["content"]
    assert "Qual o status do contrato X?" in user_content
    assert captured["model"] == retriever.settings.condensation_model


def test_condense_question_failure_degrades_to_raw_question(monkeypatch):
    def broken_chat(*args, **kwargs):
        raise RuntimeError("LM Studio indisponível")

    monkeypatch.setattr(retriever.llm, "chat", broken_chat)
    logged = {}
    monkeypatch.setattr(
        retriever.eventlog, "log_event", lambda *a, **k: logged.setdefault("called", True)
    )

    out = _condense_question(["pergunta anterior"], "e agora?")
    assert out == "e agora?"  # degrada, não propaga exceção
    assert logged.get("called") is True


# --- Integração (Postgres real, sem LM Studio) ---

@pytest.fixture
def temp_conversation():
    session = SessionLocal()
    conv = Conversation(title=None)
    session.add(conv)
    session.commit()
    session.refresh(conv)
    conv_id = conv.id
    session.close()
    yield conv_id
    session = SessionLocal()
    session.query(QueryLog).filter(QueryLog.conversation_id == conv_id).delete()
    session.query(Conversation).filter(Conversation.id == conv_id).delete()
    session.commit()
    session.close()


def test_fetch_recent_questions_orders_oldest_first(temp_conversation):
    session = SessionLocal()
    for i in range(3):
        session.add(
            QueryLog(
                question=f"pergunta {i}",
                top_k=5,
                insufficient_context=False,
                conversation_id=temp_conversation,
                turn_index=i,
            )
        )
    session.commit()
    session.close()

    session = SessionLocal()
    out = _fetch_recent_questions(session, temp_conversation, limit=4)
    session.close()
    assert out == ["pergunta 0", "pergunta 1", "pergunta 2"]


def test_fetch_recent_questions_respects_limit(temp_conversation):
    session = SessionLocal()
    for i in range(5):
        session.add(
            QueryLog(
                question=f"pergunta {i}",
                top_k=5,
                insufficient_context=False,
                conversation_id=temp_conversation,
                turn_index=i,
            )
        )
    session.commit()
    session.close()

    session = SessionLocal()
    out = _fetch_recent_questions(session, temp_conversation, limit=2)
    session.close()
    assert out == ["pergunta 3", "pergunta 4"]  # as 2 mais recentes, ordem cronológica


def test_answer_query_unknown_conversation_raises(temp_conversation):
    session = SessionLocal()
    with pytest.raises(retriever.ConversationNotFoundError):
        retriever.answer_query(session, "pergunta", None, 5, uuid.uuid4())
    session.close()


# --- Endpoints (contrato conversations, ADR-0016) ---

def test_create_and_get_conversation(client):
    resp = client.post("/conversations", json={"title": "minha conversa"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["title"] == "minha conversa"
    conv_id = body["id"]

    resp = client.get(f"/conversations/{conv_id}")
    assert resp.status_code == 200, resp.text
    detail = resp.json()
    assert detail["id"] == conv_id
    assert detail["turns"] == []

    session = SessionLocal()
    session.query(Conversation).filter(Conversation.id == uuid.UUID(conv_id)).delete()
    session.commit()
    session.close()


def test_get_conversation_unknown_404(client):
    resp = client.get(f"/conversations/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_list_conversations_has_total_count_header(client):
    resp = client.get("/conversations")
    assert resp.status_code == 200
    assert "X-Total-Count" in resp.headers


def test_query_unknown_conversation_id_404(client):
    resp = client.post(
        "/query", json={"question": "teste", "conversation_id": str(uuid.uuid4())}
    )
    assert resp.status_code == 404


# --- Fluxo completo (precisa de LM Studio real) ---

def test_query_with_conversation_id_records_turn(client):
    resp = client.post("/conversations", json={})
    conv_id = resp.json()["id"]

    resp = client.post(
        "/query", json={"question": "o que há no acervo?", "top_k": 3, "conversation_id": conv_id}
    )
    if resp.status_code == 502:
        pytest.skip("LM Studio indisponível para o retrieval/geração.")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["conversation_id"] == conv_id
    assert body["turn_index"] == 0

    detail = client.get(f"/conversations/{conv_id}").json()
    assert len(detail["turns"]) == 1
    assert detail["turns"][0]["turn_index"] == 0
    assert detail["title"] is not None  # auto-gerado da 1ª pergunta

    session = SessionLocal()
    session.query(QueryLog).filter(QueryLog.conversation_id == uuid.UUID(conv_id)).delete()
    session.query(Conversation).filter(Conversation.id == uuid.UUID(conv_id)).delete()
    session.commit()
    session.close()


def test_second_turn_condenses_and_increments_turn_index(client):
    """Ponta a ponta: 2º turno de uma conversa passa por condensação (turn_index > 0, ADR-0017)
    e o turn_index é sequencial — end-to-end contra LM Studio real (não mockado)."""
    conv_id = client.post("/conversations", json={}).json()["id"]

    resp1 = client.post(
        "/query",
        json={"question": "o que há no acervo sobre contratos?", "top_k": 3, "conversation_id": conv_id},
    )
    if resp1.status_code == 502:
        pytest.skip("LM Studio indisponível para o retrieval/geração.")
    assert resp1.status_code == 200, resp1.text
    assert resp1.json()["turn_index"] == 0

    resp2 = client.post(
        "/query",
        json={"question": "e quem é o responsável por isso?", "top_k": 3, "conversation_id": conv_id},
    )
    assert resp2.status_code == 200, resp2.text
    assert resp2.json()["turn_index"] == 1

    detail = client.get(f"/conversations/{conv_id}").json()
    assert [t["turn_index"] for t in detail["turns"]] == [0, 1]

    session = SessionLocal()
    session.query(QueryLog).filter(QueryLog.conversation_id == uuid.UUID(conv_id)).delete()
    session.query(Conversation).filter(Conversation.id == uuid.UUID(conv_id)).delete()
    session.commit()
    session.close()


def test_query_without_conversation_id_stays_stateless(client):
    """Retrocompatibilidade: uso sem conversation_id continua sem gravar conversation_id/turn_index."""
    resp = client.post("/query", json={"question": "o que há no acervo?", "top_k": 3})
    if resp.status_code == 502:
        pytest.skip("LM Studio indisponível para o retrieval/geração.")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["conversation_id"] is None
    assert body["turn_index"] is None
