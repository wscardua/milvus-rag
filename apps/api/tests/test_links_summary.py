"""WORK-011: links_summary (count + types) em GET /documents (ADR-0008).

Integração via TestClient contra o stack real (Postgres). Não requer LM Studio.
"""
from __future__ import annotations

import io


def _upload(client, process_id, **extra):
    files = {"file": ("wk011.txt", io.BytesIO(b"conteudo work-011"), "text/plain")}
    data = {"delivery_process_id": process_id, "doc_type": "Outro", **extra}
    resp = client.post("/documents", data=data, files=files)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _list_entry(client, doc_id):
    listing = client.get("/documents", params={"limit": 200})
    assert listing.status_code == 200
    by_id = {d["id"]: d for d in listing.json()}
    assert doc_id in by_id, "documento não apareceu na listagem"
    return by_id[doc_id]


def test_document_without_links_has_empty_summary(client, process_id):
    doc = _upload(client, process_id)
    try:
        entry = _list_entry(client, doc["id"])
        assert entry["links_summary"] == {"count": 0, "types": []}
    finally:
        client.delete(f"/documents/{doc['id']}")


def test_links_summary_counts_both_directions_and_types(client, process_id):
    doc_a = _upload(client, process_id)
    doc_b = _upload(client, process_id)
    try:
        resp = client.post(
            f"/documents/{doc_a['id']}/links",
            json={"target_document_id": doc_b["id"], "link_type": "esclarece"},
        )
        assert resp.status_code == 201, resp.text

        # origem (doc_a) e alvo (doc_b) contam o vínculo — semântica bidirecional (ADR-0008)
        entry_a = _list_entry(client, doc_a["id"])
        assert entry_a["links_summary"] == {"count": 1, "types": ["esclarece"]}
        entry_b = _list_entry(client, doc_b["id"])
        assert entry_b["links_summary"] == {"count": 1, "types": ["esclarece"]}
    finally:
        client.delete(f"/documents/{doc_a['id']}")
        client.delete(f"/documents/{doc_b['id']}")


def test_links_summary_includes_substitui_type(client, process_id):
    doc_a = _upload(client, process_id)
    doc_b = _upload(client, process_id)
    try:
        resp = client.post(
            f"/documents/{doc_a['id']}/links",
            json={"target_document_id": doc_b["id"], "link_type": "substitui"},
        )
        assert resp.status_code == 201, resp.text

        entry_a = _list_entry(client, doc_a["id"])
        assert "substitui" in entry_a["links_summary"]["types"]
    finally:
        client.delete(f"/documents/{doc_a['id']}")
        client.delete(f"/documents/{doc_b['id']}")
