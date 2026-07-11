"""WORK-007: delivery_phase + valid_until (ADR-0014), filtro por fase e paginação.

Integração via TestClient contra o stack real (Postgres). Não requer LM Studio.
"""
from __future__ import annotations

import io
import uuid

import pytest

from app.db.base import SessionLocal
from app.db.models import DELIVERY_PHASES, Document, IngestionJob


def _upload(client, process_id, **extra):
    files = {"file": ("wk007.txt", io.BytesIO(b"conteudo work-007"), "text/plain")}
    data = {"delivery_process_id": process_id, "doc_type": "Outro", **extra}
    return client.post("/documents", data=data, files=files)


def _cancel_pending_job(document_id: str) -> None:
    """Cancela o `ingestion_job=pending` criado pelo upload (marca `failed`).

    Usado em testes que simulam "documento já indexado" upsertando manualmente um chunk
    fake no Milvus: sem isso, o `ingestion_job=pending` real fica na fila e, se houver um
    worker de verdade rodando (ex.: ambiente de dev do usuário), ele reprocessa o documento
    de teste em paralelo — apaga o chunk fake (delete-then-upsert idempotente) e substitui
    por um chunk_id diferente, quebrando a asserção do teste por corrida, não por bug real.
    """
    session = SessionLocal()
    try:
        session.query(IngestionJob).filter(IngestionJob.document_id == document_id).update(
            {"state": "failed"}
        )
        session.commit()
    finally:
        session.close()


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


def test_patch_syncs_milvus_payload_for_already_indexed_document(client, process_id):
    """WORK-010: PATCH deixava o payload do Milvus obsoleto ao editar category_id/delivery_phase
    de um documento já indexado — corrigido via vectorstore.sync_document_fields."""
    import uuid as uuid_mod

    from app.services import vectorstore

    category_id = client.get("/categories").json()[0]["id"]
    doc = _upload(client, process_id).json()
    _cancel_pending_job(doc["id"])  # evita corrida com um worker real rodando em paralelo
    try:
        # simula "já indexado": upsert manual de um chunk no Milvus para este documento
        row = {
            "chunk_id": uuid_mod.uuid4().hex,
            "vector": [0.1] * 768,
            "document_id": doc["id"],
            "squad_id": "",
            "delivery_process_id": "",
            "category_id": "",
            "doc_type": "",
        }
        vectorstore.upsert_chunks([row])
        vectorstore._c().flush(vectorstore.settings.milvus_collection)

        resp = client.patch(
            f"/documents/{doc['id']}",
            json={"category_id": category_id, "delivery_phase": "Deploy"},
        )
        assert resp.status_code == 200, resp.text
        vectorstore._c().flush(vectorstore.settings.milvus_collection)

        hits = vectorstore.search(
            [0.1] * 768, top_k=10, filters={"category_id": category_id, "delivery_phase": "Deploy"}
        )
        assert row["chunk_id"] in {h["chunk_id"] for h in hits}
    finally:
        vectorstore._c().delete(
            collection_name=vectorstore.settings.milvus_collection, filter=f'document_id == "{doc["id"]}"'
        )
        vectorstore._c().flush(vectorstore.settings.milvus_collection)
        client.delete(f"/documents/{doc['id']}")


def test_patch_tags_updates_postgres(client, process_id):
    """WORK-010: tags passa a ser editável via PATCH (antes só existia no upload)."""
    doc = _upload(client, process_id, tags="antiga1,antiga2").json()
    try:
        resp = client.patch(f"/documents/{doc['id']}", json={"tags": ["nova1", "nova2", "nova3"]})
        assert resp.status_code == 200, resp.text
        assert resp.json()["tags"] == ["nova1", "nova2", "nova3"]
        got = client.get(f"/documents/{doc['id']}").json()
        assert got["tags"] == ["nova1", "nova2", "nova3"]
    finally:
        client.delete(f"/documents/{doc['id']}")


def test_patch_tags_empty_list_clears_tags(client, process_id):
    doc = _upload(client, process_id, tags="vai-sumir").json()
    try:
        resp = client.patch(f"/documents/{doc['id']}", json={"tags": []})
        assert resp.status_code == 200, resp.text
        assert resp.json()["tags"] == []
    finally:
        client.delete(f"/documents/{doc['id']}")


def test_patch_tags_strips_and_drops_empty_entries(client, process_id):
    doc = _upload(client, process_id).json()
    try:
        resp = client.patch(f"/documents/{doc['id']}", json={"tags": [" espaco ", "", "  ", "ok"]})
        assert resp.status_code == 200, resp.text
        assert resp.json()["tags"] == ["espaco", "ok"]
    finally:
        client.delete(f"/documents/{doc['id']}")


def test_patch_tags_does_not_touch_classification_source(client, process_id):
    doc = _upload(client, process_id).json()
    try:
        before = client.get(f"/documents/{doc['id']}").json()["classification_source"]
        client.patch(f"/documents/{doc['id']}", json={"tags": ["x"]})
        after = client.get(f"/documents/{doc['id']}").json()["classification_source"]
        assert after == before  # tags é entrada do usuário desde o upload, não classificação IA
    finally:
        client.delete(f"/documents/{doc['id']}")


def test_patch_tags_syncs_milvus_payload_and_can_be_cleared(client, process_id):
    """WORK-010: editar tags de documento já indexado atualiza o campo dinâmico no Milvus;
    limpar (tags=[]) remove o campo — o chunk continua existindo no índice.

    Usa `query()` (filtro escalar direto) em vez de `search()` (ANN por similaridade) — mais
    direto para checar o payload de um chunk_id específico, sem depender do índice HNSW.
    `_cancel_pending_job` evita a corrida real encontrada ao rodar a suíte completa: o
    upload cria um `ingestion_job=pending` de verdade, e se houver um worker real ativo em
    paralelo (ambiente de dev), ele reprocessa o documento de teste e substitui o chunk fake
    por um `chunk_id` novo — não era bug no `sync_document_fields`, era o worker de produção
    correndo por cima do teste.
    """
    from app.services import vectorstore

    def _tags_of(chunk_id: str) -> str | None:
        rows = vectorstore._c().query(
            collection_name=vectorstore.settings.milvus_collection,
            filter=f'chunk_id == "{chunk_id}"',
            output_fields=["*"],
        )
        return rows[0].get("tags") if rows else None

    doc = _upload(client, process_id, tags="original").json()
    _cancel_pending_job(doc["id"])  # evita corrida com um worker real rodando em paralelo
    try:
        row = {
            "chunk_id": uuid.uuid4().hex,
            "vector": [0.1] * 768,
            "document_id": doc["id"],
            "squad_id": "",
            "delivery_process_id": "",
            "category_id": "",
            "doc_type": "",
            "tags": vectorstore.serialize_tags(["original"]),
        }
        vectorstore.upsert_chunks([row])
        vectorstore._c().flush(vectorstore.settings.milvus_collection)
        assert _tags_of(row["chunk_id"]) == ",original,"

        resp = client.patch(f"/documents/{doc['id']}", json={"tags": ["renovada"]})
        assert resp.status_code == 200, resp.text
        vectorstore._c().flush(vectorstore.settings.milvus_collection)
        assert _tags_of(row["chunk_id"]) == ",renovada,"

        # limpar tags (PATCH tags=[]) remove o campo dinâmico, mas não o chunk
        resp2 = client.patch(f"/documents/{doc['id']}", json={"tags": []})
        assert resp2.status_code == 200, resp2.text
        vectorstore._c().flush(vectorstore.settings.milvus_collection)
        assert _tags_of(row["chunk_id"]) is None  # campo removido
        still_there = vectorstore._c().query(
            collection_name=vectorstore.settings.milvus_collection,
            filter=f'chunk_id == "{row["chunk_id"]}"',
            output_fields=["chunk_id"],
        )
        assert len(still_there) == 1  # chunk continua existindo (só o campo tags sumiu)
    finally:
        vectorstore._c().delete(
            collection_name=vectorstore.settings.milvus_collection, filter=f'document_id == "{doc["id"]}"'
        )
        vectorstore._c().flush(vectorstore.settings.milvus_collection)
        client.delete(f"/documents/{doc['id']}")


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
