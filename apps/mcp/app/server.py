"""Servidor MCP de consulta ao acervo (FEAT-MCP-001, ADR-0005).

Expõe 10 tools que agentes consomem para pesquisar e navegar os documentos
vetorizados/categorizados: 4 de consulta (search_documents/retrieve_chunks/
list_documents/get_document) e 6 de lookup (WORK-010 — list_squads/
list_delivery_processes/list_categories/list_doc_types/list_delivery_phases/
list_tags), para resolver nome→id antes de filtrar. Cada tool é apenas uma
chamada HTTP à API FastAPI — o retrieval, a geração e as citações vêm prontos
de lá (fonte da verdade).

Executar (stdio, default):
    cd apps/mcp && python -m app.server
"""
# NB: sem `from __future__ import annotations` — o FastMCP inspeciona as anotações
# reais dos parâmetros das tools; com anotações adiadas (strings) ele quebra ao
# testar `issubclass(...)` num `dict | None`.

from mcp.server.fastmcp import FastMCP

from app.client import ApiError
from app import client
from app.config import settings

mcp = FastMCP("milvus-rag")


# `filters` (dict, opcional) nas tools de consulta abaixo: `squad`/`delivery_process`/`category`
# (UUID — resolva o nome com list_squads/list_delivery_processes/list_categories antes de
# filtrar); `doc_type`/`delivery_phase` (string, lista fechada — veja list_doc_types/
# list_delivery_phases); `tags` (lista de strings, semântica OR — documento com qualquer uma
# das tags pedidas; veja list_tags). Sem resolver nome→id primeiro, o agente não consegue
# filtrar por squad/delivery_process (a API exige UUID, não o nome).


@mcp.tool()
def search_documents(
    question: str, filters: dict | None = None, top_k: int | None = None
) -> dict:
    """Pergunta em linguagem natural ao acervo; devolve resposta gerada + citações.

    A resposta é ancorada nos documentos (grounding): sempre acompanha `citations`
    (chunk + documento de origem) e `linked_flow` (documentos vinculados considerados).
    `filters` opcional: squad, delivery_process, category (UUID — resolva com
    list_squads/list_delivery_processes/list_categories), doc_type, delivery_phase (string,
    veja list_doc_types/list_delivery_phases), tags (lista de strings, OR — veja list_tags).
    Se não houver contexto suficiente, `insufficient_context=true` e `answer=null`.
    """
    try:
        return client.query(question, filters, top_k)
    except ApiError as exc:
        raise RuntimeError(str(exc)) from exc


@mcp.tool()
def retrieve_chunks(
    question: str, filters: dict | None = None, top_k: int | None = None
) -> dict:
    """Recupera apenas os trechos (chunks) mais relevantes, SEM gerar resposta.

    Para o agente montar o próprio prompt. Cada trecho traz `document_id`, `chunk_id`,
    `text` e `score`. `insufficient_context=true` quando nada supera o limiar.
    `filters` opcional: squad, delivery_process, category (UUID — resolva com
    list_squads/list_delivery_processes/list_categories), doc_type, delivery_phase (string,
    veja list_doc_types/list_delivery_phases), tags (lista de strings, OR — veja list_tags).
    """
    try:
        return client.retrieve(question, filters, top_k)
    except ApiError as exc:
        raise RuntimeError(str(exc)) from exc


@mcp.tool()
def list_documents(filters: dict | None = None) -> list:
    """Lista os documentos do acervo, com filtros por categoria/metadado.

    `filters` opcional: squad, delivery_process, category (UUID — resolva com
    list_squads/list_delivery_processes/list_categories), doc_type, delivery_phase (string,
    veja list_doc_types/list_delivery_phases), tags (lista de strings, OR — veja list_tags),
    limit, offset. Retorna metadados e estado de ingestão de cada documento.
    """
    try:
        return client.list_documents(filters)
    except ApiError as exc:
        raise RuntimeError(str(exc)) from exc


@mcp.tool()
def get_document(document_id: str) -> dict:
    """Metadados e estado de ingestão de um documento pelo seu id."""
    try:
        return client.get_document(document_id)
    except ApiError as exc:
        raise RuntimeError(str(exc)) from exc


# --- Tools de lookup (WORK-010) — resolvem nome→id/valores válidos antes de filtrar acima ---


@mcp.tool()
def list_squads() -> list:
    """Lista as squads cadastradas (`id`, `name`, ...). Use o `id` no filtro `squad`."""
    try:
        return client.list_squads()
    except ApiError as exc:
        raise RuntimeError(str(exc)) from exc


@mcp.tool()
def list_delivery_processes(squad_id: str | None = None) -> list:
    """Lista os processos de delivery (`id`, `squad_id`, `name`, ...), opcionalmente por squad.

    Use o `id` no filtro `delivery_process`.
    """
    try:
        return client.list_delivery_processes(squad_id)
    except ApiError as exc:
        raise RuntimeError(str(exc)) from exc


@mcp.tool()
def list_categories() -> list:
    """Lista as categorias da taxonomia (`id`, `name`). Use o `id` no filtro `category`."""
    try:
        return client.list_categories()
    except ApiError as exc:
        raise RuntimeError(str(exc)) from exc


@mcp.tool()
def list_doc_types() -> list:
    """Lista fechada de `doc_type` válidos — use um destes valores no filtro `doc_type`."""
    try:
        return client.list_doc_types()
    except ApiError as exc:
        raise RuntimeError(str(exc)) from exc


@mcp.tool()
def list_delivery_phases() -> list:
    """Lista fechada de fases de delivery — use um destes valores no filtro `delivery_phase`."""
    try:
        return client.list_delivery_phases()
    except ApiError as exc:
        raise RuntimeError(str(exc)) from exc


@mcp.tool()
def list_tags() -> list:
    """Tags distintas já usadas no acervo — use uma ou mais no filtro `tags` (semântica OR)."""
    try:
        return client.list_tags()
    except ApiError as exc:
        raise RuntimeError(str(exc)) from exc


def main() -> None:
    mcp.run(transport=settings.mcp_transport)


if __name__ == "__main__":
    main()
