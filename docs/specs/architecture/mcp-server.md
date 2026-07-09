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
| `retrieve_chunks(question, top_k?)` | `POST /query` (só trechos) | chunks relevantes sem geração |

## Configuração

- `API_BASE_URL` (ex.: `http://localhost:8000`).
- Transporte: stdio por padrão; HTTP/SSE configurável.

## Fronteiras

- É cliente, como o Django. FastAPI continua fonte da verdade.
- Reusa os contratos `query-and-citations` e `upload-and-metadata`.
- Grounding/citações vêm prontos da API.
