# Arquitetura — Servidor MCP (`apps/mcp/`)

Canal de consulta ao acervo para **outros agentes**, via Model Context Protocol. Cliente HTTP da API FastAPI (ADR-0005).

## Papel

- Expor tools MCP que agentes consomem para pesquisar e navegar os documentos vetorizados/categorizados.
- **Não** implementa retrieval nem acessa Milvus/Postgres — traduz cada tool numa chamada HTTP à API.

## Tools

| Tool | Chamada na API | Retorno |
|---|---|---|
| `search_documents(question, filters?, top_k?)` | `POST /query` | resposta + citações |
| `list_documents(filters?)` | `GET /documents` | acervo por categoria/metadado |
| `get_document(id)` | `GET /documents/{id}` | metadados + estado |
| `retrieve_chunks(question, filters?, top_k?)` | `POST /retrieve` | chunks relevantes sem geração |

Implementação em `apps/mcp/app/`: `server.py` (FastMCP, registra as 4 tools), `client.py` (cliente HTTP + tradução de filtros), `config.py` (env). Roda via stdio: `python -m app.server`.

## Configuração

- `API_BASE_URL` (dev local: `http://localhost:8001` — a API roda na 8001; a UI Django na 8000).
- `MCP_TRANSPORT`: `stdio` por padrão; `http`/`sse` como evolução (a POC é local, sem auth).
- NB: o `venv/` é compartilhado com `apps/api`; o SDK `mcp` fixa `starlette`/`sse-starlette` no range compatível com o FastAPI (ver `apps/mcp/requirements.txt`).

## Fronteiras

- É cliente, como o Django. FastAPI continua fonte da verdade.
- Reusa os contratos `query-and-citations` e `upload-and-metadata`.
- Grounding/citações vêm prontos da API.
