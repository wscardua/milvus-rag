"""WORK-010 / ADR-0015: GET /tags e filtro de tags em GET /documents.

Integração via TestClient contra o stack real (Postgres). Não requer LM Studio nem Milvus.
"""
from __future__ import annotations

import io

import pytest


def _upload(client, process_id, **extra):
    files = {"file": ("wk010.txt", io.BytesIO(b"conteudo work-010"), "text/plain")}
    data = {"delivery_process_id": process_id, "doc_type": "Outro", **extra}
    return client.post("/documents", data=data, files=files)


def test_tags_endpoint_returns_distinct_sorted(client, process_id):
    doc1 = _upload(client, process_id, tags="zzz,billing").json()
    doc2 = _upload(client, process_id, tags="billing,api").json()
    try:
        resp = client.get("/tags")
        assert resp.status_code == 200
        tags = resp.json()
        assert tags == sorted(tags)  # ordenado
        assert {"zzz", "billing", "api"}.issubset(set(tags))
        assert tags.count("billing") == 1  # distinct
    finally:
        client.delete(f"/documents/{doc1['id']}")
        client.delete(f"/documents/{doc2['id']}")


def test_list_documents_filter_by_single_tag(client, process_id):
    doc = _upload(client, process_id, tags="wk010-unico").json()
    try:
        listing = client.get("/documents", params={"tags": ["wk010-unico"], "limit": 100})
        assert listing.status_code == 200
        ids = {d["id"] for d in listing.json()}
        assert doc["id"] in ids
    finally:
        client.delete(f"/documents/{doc['id']}")


def test_list_documents_filter_by_multiple_tags_is_or(client, process_id):
    doc_a = _upload(client, process_id, tags="wk010-a").json()
    doc_b = _upload(client, process_id, tags="wk010-b").json()
    doc_c = _upload(client, process_id, tags="wk010-c").json()
    try:
        listing = client.get(
            "/documents", params={"tags": ["wk010-a", "wk010-b"], "limit": 100}
        )
        ids = {d["id"] for d in listing.json()}
        assert doc_a["id"] in ids
        assert doc_b["id"] in ids
        assert doc_c["id"] not in ids
    finally:
        client.delete(f"/documents/{doc_a['id']}")
        client.delete(f"/documents/{doc_b['id']}")
        client.delete(f"/documents/{doc_c['id']}")


def test_list_documents_no_tags_filter_unaffected(client, process_id):
    listing = client.get("/documents", params={"limit": 1})
    assert listing.status_code == 200
