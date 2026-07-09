"""Testes do ciclo de vida do documento: arquivo (view/download) e exclusão (ADR-0010)."""
from __future__ import annotations

import uuid

from app.db.base import SessionLocal
from app.db.models import Chunk, Document, IngestionJob


def test_get_file_inline_and_attachment(client, temp_document):
    did = temp_document["id"]

    inline = client.get(f"/documents/{did}/file")
    assert inline.status_code == 200
    assert inline.headers["content-disposition"].startswith("inline")
    assert inline.content == b"conteudo de teste do pytest"

    attach = client.get(f"/documents/{did}/file", params={"download": "true"})
    assert attach.status_code == 200
    assert attach.headers["content-disposition"].startswith("attachment")


def test_get_file_missing_document_404(client):
    resp = client.get(f"/documents/{uuid.uuid4()}/file")
    assert resp.status_code == 404


def test_delete_document_cascade(client, process_id):
    import io

    files = {"file": ("del_test.txt", io.BytesIO(b"apagar depois"), "text/plain")}
    doc = client.post("/documents", data={"delivery_process_id": process_id}, files=files).json()
    did = doc["id"]

    # há um ingestion_job pending logo após o upload
    session = SessionLocal()
    assert session.query(IngestionJob).filter_by(document_id=uuid.UUID(did)).count() == 1
    session.close()

    resp = client.delete(f"/documents/{did}")
    assert resp.status_code == 204

    # cascade: document, chunk e ingestion_job zerados
    session = SessionLocal()
    du = uuid.UUID(did)
    assert session.query(Document).filter_by(id=du).count() == 0
    assert session.query(Chunk).filter_by(document_id=du).count() == 0
    assert session.query(IngestionJob).filter_by(document_id=du).count() == 0
    session.close()

    # reexclusão é 404
    assert client.delete(f"/documents/{did}").status_code == 404
    assert client.get(f"/documents/{did}").status_code == 404


def test_delete_missing_document_404(client):
    assert client.delete(f"/documents/{uuid.uuid4()}").status_code == 404
