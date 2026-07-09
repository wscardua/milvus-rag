"""Cliente HTTP da API FastAPI (ADR-0005).

O MCP não fala com Milvus/Postgres nem reimplementa retrieval: cada tool vira uma
chamada HTTP aqui. Falhas viram `ApiError` com mensagem clara — o servidor MCP
repassa o erro ao agente em vez de inventar resposta (grounding).
"""
from __future__ import annotations

import httpx

from app.config import settings


class ApiError(RuntimeError):
    """Falha ao falar com a API (indisponível, timeout ou status >= 400)."""


def _request(method: str, path: str, **kwargs) -> dict | list:
    url = f"{settings.api_base_url.rstrip('/')}{path}"
    try:
        with httpx.Client(timeout=settings.api_timeout_seconds) as http:
            resp = http.request(method, url, **kwargs)
    except httpx.RequestError as exc:  # API fora do ar, DNS, timeout de conexão…
        raise ApiError(f"API indisponível em {settings.api_base_url}: {exc}") from exc
    if resp.status_code >= 400:
        # repassa o detalhe da API sem mascarar o status
        raise ApiError(f"API respondeu {resp.status_code}: {resp.text}")
    try:
        return resp.json()
    except ValueError as exc:  # corpo 200 não-JSON (proxy/gateway) → mantém o contrato ApiError
        raise ApiError(f"Resposta não-JSON da API ({resp.status_code}): {resp.text[:200]}") from exc


def query(question: str, filters: dict | None = None, top_k: int | None = None) -> dict:
    """POST /query → resposta gerada + citações (grounding)."""
    body: dict = {"question": question}
    if filters:
        body["filters"] = filters
    if top_k is not None:
        body["top_k"] = top_k
    return _request("POST", "/query", json=body)


def retrieve(question: str, filters: dict | None = None, top_k: int | None = None) -> dict:
    """POST /retrieve → apenas trechos relevantes, sem geração."""
    body: dict = {"question": question}
    if filters:
        body["filters"] = filters
    if top_k is not None:
        body["top_k"] = top_k
    return _request("POST", "/retrieve", json=body)


def list_documents(filters: dict | None = None) -> list:
    """GET /documents → acervo por categoria/metadado.

    Traduz os filtros do contrato para os query params da API
    (squad → squad_id, delivery_process → delivery_process_id, category → category_id).
    """
    param_map = {
        "squad": "squad_id",
        "delivery_process": "delivery_process_id",
        "category": "category_id",
        "doc_type": "doc_type",
        "limit": "limit",
        "offset": "offset",
    }
    params = {param_map[k]: v for k, v in (filters or {}).items() if k in param_map and v is not None}
    return _request("GET", "/documents", params=params)


def get_document(document_id: str) -> dict:
    """GET /documents/{id} → metadados + estado de ingestão."""
    return _request("GET", f"/documents/{document_id}")
