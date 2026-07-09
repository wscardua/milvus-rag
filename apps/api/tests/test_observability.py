"""Testes de observabilidade: /health por serviço e /logs (ADR-0011)."""
from __future__ import annotations

from app.services import eventlog


def test_health_reports_components_and_queue(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in ("ok", "degraded")
    names = {c["name"] for c in body["components"]}
    assert {"postgres", "milvus", "lm_studio", "worker"} <= names
    for c in body["components"]:
        assert set(c) >= {"name", "ok", "detail"}
    assert set(body["queue"]) == {"pending", "processing", "indexed", "failed"}


def test_logs_lists_events_with_filter(client):
    # gera um evento conhecido e confirma que aparece filtrando por componente
    eventlog.log_event("INFO", "api", "pytest_probe", "evento de teste")
    resp = client.get("/logs", params={"component": "api", "limit": 50})
    assert resp.status_code == 200
    rows = resp.json()
    assert any(r["event"] == "pytest_probe" for r in rows)
    assert all(r["component"] == "api" for r in rows)


def test_logs_level_filter(client):
    resp = client.get("/logs", params={"level": "ERROR", "limit": 10})
    assert resp.status_code == 200
    assert all(r["level"] == "ERROR" for r in resp.json())
