"""Servidor MCP de consulta ao acervo (FEAT-MCP-001, ADR-0005).

Expõe 4 tools que agentes consomem para pesquisar e navegar os documentos
vetorizados/categorizados. Cada tool é apenas uma chamada HTTP à API FastAPI —
o retrieval, a geração e as citações vêm prontos de lá (fonte da verdade).

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


@mcp.tool()
def search_documents(
    question: str, filters: dict | None = None, top_k: int | None = None
) -> dict:
    """Pergunta em linguagem natural ao acervo; devolve resposta gerada + citações.

    A resposta é ancorada nos documentos (grounding): sempre acompanha `citations`
    (chunk + documento de origem) e `linked_flow` (documentos vinculados considerados).
    `filters` opcional: squad, delivery_process, category, doc_type, tags.
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
    """
    try:
        return client.retrieve(question, filters, top_k)
    except ApiError as exc:
        raise RuntimeError(str(exc)) from exc


@mcp.tool()
def list_documents(filters: dict | None = None) -> list:
    """Lista os documentos do acervo, com filtros por categoria/metadado.

    `filters` opcional: squad, delivery_process, category, doc_type, limit, offset.
    Retorna metadados e estado de ingestão de cada documento.
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


def main() -> None:
    mcp.run(transport=settings.mcp_transport)


if __name__ == "__main__":
    main()
