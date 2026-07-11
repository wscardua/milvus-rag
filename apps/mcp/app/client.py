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
        "delivery_phase": "delivery_phase",  # ADR-0015
        "tags": "tags",  # ADR-0015 — lista; httpx envia como múltiplos ?tags=
        "limit": "limit",
        "offset": "offset",
    }
    params = {param_map[k]: v for k, v in (filters or {}).items() if k in param_map and v is not None}
    return _request("GET", "/documents", params=params)


def get_document(document_id: str) -> dict:
    """GET /documents/{id} → metadados + estado de ingestão."""
    return _request("GET", f"/documents/{document_id}")


# --- Tools de lookup (WORK-010) — proxy fino dos GETs de organization-admin ---
# Para o agente resolver nome→id antes de filtrar squad/delivery_process nas tools de consulta.


def list_squads() -> list:
    """GET /squads → squads cadastradas."""
    return _request("GET", "/squads")


def list_delivery_processes(squad_id: str | None = None) -> list:
    """GET /delivery-processes?squad_id= → processos de delivery, filtrável por squad."""
    params = {"squad_id": squad_id} if squad_id else None
    return _request("GET", "/delivery-processes", params=params)


def list_categories() -> list:
    """GET /categories → categorias da taxonomia."""
    return _request("GET", "/categories")


def list_doc_types() -> list:
    """GET /doc-types → lista fechada de doc_type."""
    return _request("GET", "/doc-types")


def list_delivery_phases() -> list:
    """GET /delivery-phases → lista fechada de fases de delivery (ADR-0014/0015)."""
    return _request("GET", "/delivery-phases")


def list_tags() -> list:
    """GET /tags → tags distintas já usadas no acervo (ADR-0015)."""
    return _request("GET", "/tags")
