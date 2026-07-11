"""WORK-007: delivery_phase + valid_until (ADR-0014), filtro por fase e paginação.

Integração via TestClient contra o stack real (Postgres). Não requer LM Studio.
"""
from __future__ import annotations

import io
import uuid

import pytest

from app.db.base import SessionLocal
from app.db.models import DELIVERY_PHASES, Document


def _upload(client, process_id, **extra):
    files = {"file": ("wk007.txt", io.BytesIO(b"conteudo work-007"), "text/plain")}
    data = {"delivery_process_id": process_id, "doc_type": "Outro", **extra}
    return client.post("/documents", data=data, files=files)


def test_delivery_phases_endpoint(client):
    resp = client.get("/delivery-phases")
    assert resp.status_code == 200
    assert resp.json() == list(DELIVERY_PHASES)


def test_upload_with_phase_and_valid_until(client, process_id):
    resp = _upload(client, process_id, delivery_phase="Testes", valid_until="2030-12-31")
    assert resp.status_code == 201, resp.text
    doc = resp.json()
    try:
        assert doc["delivery_phase"] == "Testes"
        assert doc["valid_until"] == "2030-12-31"
        # persistido também na leitura
        got = client.get(f"/documents/{doc['id']}").json()
        assert got["delivery_phase"] == "Testes"
        assert got["valid_until"] == "2030-12-31"
    finally:
        client.delete(f"/documents/{doc['id']}")


def test_upload_invalid_phase_422(client, process_id):
    resp = _upload(client, process_id, delivery_phase="Fase Inexistente")
    assert resp.status_code == 422


def test_upload_invalid_valid_until_422(client, process_id):
    resp = _upload(client, process_id, valid_until="31/12/2030")  # não-ISO
    assert resp.status_code == 422


def test_list_filter_by_phase_and_total_count_header(client, process_id):
    phase = "Refinamento Técnico"
    resp = _upload(client, process_id, delivery_phase=phase)
    doc = resp.json()
    try:
        listing = client.get("/documents", params={"delivery_phase": phase, "limit": 100})
        assert listing.status_code == 200
        assert "x-total-count" in {k.lower() for k in listing.headers}
        ids = {d["id"] for d in listing.json()}
        assert doc["id"] in ids
        assert all(d["delivery_phase"] == phase for d in listing.json())
    finally:
        client.delete(f"/documents/{doc['id']}")


def test_pagination_limit_offset(client, process_id):
    listing = client.get("/documents", params={"limit": 1, "offset": 0})
    assert listing.status_code == 200
    assert len(listing.json()) <= 1
    total = int(listing.headers["X-Total-Count"])
    assert total >= 0


def test_patch_delivery_does_not_touch_classification_source(client, process_id):
    doc = _upload(client, process_id).json()
    try:
        # antes: classification_source None (ingestão/LLM ainda não rodou no teste)
        before = client.get(f"/documents/{doc['id']}").json()["classification_source"]
        resp = client.patch(
            f"/documents/{doc['id']}",
            json={"delivery_phase": "Deploy", "valid_until": "2028-01-01"},
        )
        assert resp.status_code == 200, resp.text
        after = client.get(f"/documents/{doc['id']}").json()
        assert after["delivery_phase"] == "Deploy"
        assert after["valid_until"] == "2028-01-01"
        # editar só fase/vigência NÃO marca override de classificação (ADR-0014)
        assert after["classification_source"] == before
    finally:
        client.delete(f"/documents/{doc['id']}")


def test_patch_invalid_phase_422(client, process_id):
    doc = _upload(client, process_id).json()
    try:
        resp = client.patch(f"/documents/{doc['id']}", json={"delivery_phase": "xpto"})
        assert resp.status_code == 422
    finally:
        client.delete(f"/documents/{doc['id']}")


def test_demote_expired_reranks(client, process_id):
    """_demote_expired rebaixa o vencido e reordena pelo score ajustado (ADR-0014)."""
    from app.config import settings
    from app.domain.retrieval import retriever

    expired = _upload(client, process_id, valid_until="2000-01-01").json()
    valid = _upload(client, process_id, valid_until="2999-01-01").json()
    try:
        # o vencido começa à frente (score maior); após o rebaixamento o vigente assume o topo
        hits = [
            {"chunk_id": "c-exp", "document_id": expired["id"], "score": 0.90},
            {"chunk_id": "c-val", "document_id": valid["id"], "score": 0.80},
        ]
        session = SessionLocal()
        try:
            out = retriever._demote_expired(session, hits)
        finally:
            session.close()
        by_doc = {h["document_id"]: h["score"] for h in out}
        assert by_doc[expired["id"]] == pytest.approx(0.90 * settings.retrieval_expired_score_factor)
        assert by_doc[valid["id"]] == pytest.approx(0.80)  # inalterado
        assert out[0]["document_id"] == valid["id"]  # vigente reordenado para o topo
    finally:
        client.delete(f"/documents/{expired['id']}")
        client.delete(f"/documents/{valid['id']}")
