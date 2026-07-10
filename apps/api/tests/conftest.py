"""Fixtures de teste (integração contra o stack real: Postgres/Milvus/LM Studio).

Rodar de dentro de apps/api com a infra de pip:
    source ../../venv/bin/activate && pytest
"""
from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="session")
def process_id(client: TestClient) -> str:
    """Um delivery_process existente; pula os testes se não houver taxonomia/org seedada."""
    resp = client.get("/delivery-processes")
    resp.raise_for_status()
    procs = resp.json()
    if not procs:
        pytest.skip("Sem delivery_process — rode o seed/organização antes.")
    return procs[0]["id"]


@pytest.fixture
def temp_document(client: TestClient, process_id: str):
    """Cria um documento descartável e garante a remoção ao final do teste."""
    files = {"file": ("teste_pytest.txt", io.BytesIO(b"conteudo de teste do pytest"), "text/plain")}
    resp = client.post(
        "/documents",
        data={"delivery_process_id": process_id, "doc_type": "Outro"},  # doc_type obrigatório (ADR-0013)
        files=files,
    )
    assert resp.status_code == 201, resp.text
    doc = resp.json()
    yield doc
    client.delete(f"/documents/{doc['id']}")  # idempotente (404 se já removido)
