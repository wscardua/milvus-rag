"""WORK-010 / ADR-0015: integração real com o Milvus — delivery_phase/tags como campo dinâmico.

Grava vetores de teste diretamente via vectorstore.upsert_chunks/search (sem passar pelo
pipeline de ingestão completo — não depende de LM Studio) e confirma o comportamento
validado no spike técnico do ADR-0015: igualdade em delivery_phase, OR de LIKE em tags,
e que um chunk sem esses campos não aparece em busca filtrada por eles (mas continua
aparecendo em busca sem filtro).
"""
from __future__ import annotations

import uuid

import pytest

from app.services import vectorstore


def _row(**overrides) -> dict:
    base = {
        "chunk_id": uuid.uuid4().hex,
        "vector": [0.1] * 768,
        "document_id": f"doc-{uuid.uuid4().hex[:8]}",
        "squad_id": "",
        "delivery_process_id": "",
        "category_id": "",
        "doc_type": "",
    }
    base.update(overrides)
    return base


@pytest.fixture
def three_chunks():
    """3 chunks: 2 com delivery_phase/tags (fase igual, tags diferentes), 1 sem nenhum dos dois."""
    rows = [
        _row(delivery_phase="Testes", tags=vectorstore.serialize_tags(["billing", "api"])),
        _row(delivery_phase="Testes", tags=vectorstore.serialize_tags(["infra"])),
        _row(),  # sem delivery_phase/tags — simula chunk indexado antes do WORK-010
    ]
    vectorstore.upsert_chunks(rows)
    vectorstore._c().flush(vectorstore.settings.milvus_collection)
    yield rows
    for r in rows:
        vectorstore._c().delete(
            collection_name=vectorstore.settings.milvus_collection,
            filter=f'chunk_id == "{r["chunk_id"]}"',
        )
    vectorstore._c().flush(vectorstore.settings.milvus_collection)


def test_filter_by_delivery_phase_excludes_chunk_without_field(three_chunks):
    hits = vectorstore.search([0.1] * 768, top_k=10, filters={"delivery_phase": "Testes"})
    ids = {h["chunk_id"] for h in hits}
    assert three_chunks[0]["chunk_id"] in ids
    assert three_chunks[1]["chunk_id"] in ids
    assert three_chunks[2]["chunk_id"] not in ids  # sem o campo, não bate na igualdade


def test_filter_by_single_tag(three_chunks):
    hits = vectorstore.search([0.1] * 768, top_k=10, filters={"tags": ["billing"]})
    ids = {h["chunk_id"] for h in hits}
    assert three_chunks[0]["chunk_id"] in ids
    assert three_chunks[1]["chunk_id"] not in ids
    assert three_chunks[2]["chunk_id"] not in ids


def test_filter_by_multiple_tags_is_or(three_chunks):
    hits = vectorstore.search([0.1] * 768, top_k=10, filters={"tags": ["billing", "infra"]})
    ids = {h["chunk_id"] for h in hits}
    assert three_chunks[0]["chunk_id"] in ids  # tem "billing"
    assert three_chunks[1]["chunk_id"] in ids  # tem "infra"
    assert three_chunks[2]["chunk_id"] not in ids  # não tem nenhuma


def test_no_filter_returns_chunk_without_dynamic_fields_too(three_chunks):
    """Chunk sem delivery_phase/tags não pode sumir da busca geral (sem filtro)."""
    hits = vectorstore.search([0.1] * 768, top_k=10, filters=None)
    ids = {h["chunk_id"] for h in hits}
    assert three_chunks[2]["chunk_id"] in ids


def test_combined_delivery_phase_and_tags_filter(three_chunks):
    hits = vectorstore.search(
        [0.1] * 768, top_k=10, filters={"delivery_phase": "Testes", "tags": ["infra"]}
    )
    ids = {h["chunk_id"] for h in hits}
    assert three_chunks[1]["chunk_id"] in ids
    assert three_chunks[0]["chunk_id"] not in ids  # fase bate, tag não


# --- sync_document_fields (PATCH /documents/{id} deixava o payload obsoleto — corrigido aqui) ---


@pytest.fixture
def one_doc_two_chunks():
    """2 chunks do MESMO documento, category_id inicial preenchido, sem delivery_phase."""
    doc_id = f"doc-{uuid.uuid4().hex[:8]}"
    rows = [_row(document_id=doc_id, category_id="cat-old"), _row(document_id=doc_id, category_id="cat-old")]
    vectorstore.upsert_chunks(rows)
    vectorstore._c().flush(vectorstore.settings.milvus_collection)
    yield doc_id, rows
    vectorstore._c().delete(
        collection_name=vectorstore.settings.milvus_collection, filter=f'document_id == "{doc_id}"'
    )
    vectorstore._c().flush(vectorstore.settings.milvus_collection)


def test_sync_document_fields_updates_declared_field_on_all_chunks(one_doc_two_chunks):
    doc_id, rows = one_doc_two_chunks
    updated = vectorstore.sync_document_fields(doc_id, {"category_id": "cat-new"})
    assert updated == 2
    vectorstore._c().flush(vectorstore.settings.milvus_collection)

    hits = vectorstore.search([0.1] * 768, top_k=10, filters={"category_id": "cat-new"})
    ids = {h["chunk_id"] for h in hits}
    assert {r["chunk_id"] for r in rows} <= ids

    hits_old = vectorstore.search([0.1] * 768, top_k=10, filters={"category_id": "cat-old"})
    assert not ({r["chunk_id"] for r in rows} & {h["chunk_id"] for h in hits_old})


def test_sync_document_fields_sets_dynamic_field(one_doc_two_chunks):
    doc_id, rows = one_doc_two_chunks
    vectorstore.sync_document_fields(doc_id, {"delivery_phase": "Deploy"})
    vectorstore._c().flush(vectorstore.settings.milvus_collection)

    hits = vectorstore.search([0.1] * 768, top_k=10, filters={"delivery_phase": "Deploy"})
    ids = {h["chunk_id"] for h in hits}
    assert {r["chunk_id"] for r in rows} <= ids


def test_sync_document_fields_removes_dynamic_field_when_none(one_doc_two_chunks):
    doc_id, rows = one_doc_two_chunks
    vectorstore.sync_document_fields(doc_id, {"delivery_phase": "Deploy"})
    vectorstore._c().flush(vectorstore.settings.milvus_collection)

    vectorstore.sync_document_fields(doc_id, {"delivery_phase": None})
    vectorstore._c().flush(vectorstore.settings.milvus_collection)

    hits = vectorstore.search([0.1] * 768, top_k=10, filters={"delivery_phase": "Deploy"})
    assert not ({r["chunk_id"] for r in rows} & {h["chunk_id"] for h in hits})
    # continua buscável sem o filtro (campo removido, não o chunk)
    hits_all = vectorstore.search([0.1] * 768, top_k=10, filters=None)
    assert {r["chunk_id"] for r in rows} <= {h["chunk_id"] for h in hits_all}


def test_sync_document_fields_noop_when_no_chunks_indexed():
    """Documento sem chunks no Milvus ainda (não indexado) — não erra, só não faz nada."""
    assert vectorstore.sync_document_fields("doc-inexistente-xyz", {"delivery_phase": "Testes"}) == 0
