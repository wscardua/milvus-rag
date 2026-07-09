"""Testes unitários do MCP: tradução tool→HTTP e tratamento de erro (FEAT-MCP-001).

Não precisam da API no ar — o httpx é substituído por um fake que captura a
requisição ou simula falha. Cobre o §11 da spec (mapeamento tool→chamada HTTP;
tradução de filtros; API fora do ar → erro explícito).
"""
from __future__ import annotations

import httpx
import pytest

from app import client, server


class _FakeResp:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text

    def json(self):
        return self._payload


def _fake_httpx(monkeypatch, *, capture=None, resp=None, exc=None):
    """Substitui httpx.Client no módulo client por um fake controlável."""

    class _FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def request(self, method, url, **kwargs):
            if exc is not None:
                raise exc
            if capture is not None:
                capture.update(method=method, url=url, **kwargs)
            return resp if resp is not None else _FakeResp(200, {})

    monkeypatch.setattr(client.httpx, "Client", _FakeClient)


def test_list_documents_translates_filters(monkeypatch):
    cap: dict = {}
    _fake_httpx(monkeypatch, capture=cap, resp=_FakeResp(200, []))
    client.list_documents(
        {"squad": "s1", "delivery_process": "p1", "category": "c1", "doc_type": "AND", "ignorado": "x"}
    )
    assert cap["method"] == "GET"
    assert cap["url"].endswith("/documents")
    # nomes do contrato → query params da API; chave desconhecida é descartada
    assert cap["params"] == {
        "squad_id": "s1",
        "delivery_process_id": "p1",
        "category_id": "c1",
        "doc_type": "AND",
    }


def test_query_builds_body(monkeypatch):
    cap: dict = {}
    _fake_httpx(monkeypatch, capture=cap, resp=_FakeResp(200, {"answer": "ok"}))
    client.query("qual o processo?", {"doc_type": "Runbook"}, 3)
    assert cap["method"] == "POST"
    assert cap["url"].endswith("/query")
    assert cap["json"] == {"question": "qual o processo?", "filters": {"doc_type": "Runbook"}, "top_k": 3}


def test_retrieve_hits_dedicated_endpoint(monkeypatch):
    cap: dict = {}
    _fake_httpx(monkeypatch, capture=cap, resp=_FakeResp(200, {"chunks": []}))
    client.retrieve("resumo", None, None)
    assert cap["url"].endswith("/retrieve")  # endpoint dedicado, não /query
    assert cap["json"] == {"question": "resumo"}  # sem filters/top_k quando ausentes


def test_api_down_raises_apierror(monkeypatch):
    _fake_httpx(monkeypatch, exc=httpx.ConnectError("recusada"))
    with pytest.raises(client.ApiError) as exc:
        client.query("oi")
    assert "indisponível" in str(exc.value).lower()


def test_http_error_surfaced(monkeypatch):
    _fake_httpx(monkeypatch, resp=_FakeResp(502, text="falha no retrieval"))
    with pytest.raises(client.ApiError) as exc:
        client.retrieve("oi")
    assert "502" in str(exc.value)


def test_non_json_200_becomes_apierror(monkeypatch):
    """Corpo 200 não-JSON (ex.: proxy) → ApiError, não exceção crua."""
    class _BadJson(_FakeResp):
        def json(self):
            raise ValueError("Expecting value")

    _fake_httpx(monkeypatch, resp=_BadJson(200, text="<html>gateway</html>"))
    with pytest.raises(client.ApiError):
        client.query("oi")


def test_tool_translates_apierror_to_error(monkeypatch):
    """Com a API fora, a tool retorna erro explícito ao agente (não alucina)."""
    def _boom(*a, **k):
        raise client.ApiError("API indisponível em http://localhost:8001")

    monkeypatch.setattr(client, "query", _boom)
    with pytest.raises(RuntimeError) as exc:
        server.search_documents("pergunta")
    assert "indisponível" in str(exc.value).lower()
