# ADR-0005 — Canal de consulta via MCP (cliente da API)

## Contexto

Além da UI Django, os documentos vetorizados/categorizados devem ser consultáveis por **outros agentes** via um servidor **MCP** (Model Context Protocol) que a POC disponibilizará. É preciso definir como o MCP acessa o retrieval sem duplicar lógica.

## Decisão

- **O MCP é um cliente HTTP da API FastAPI** — chama `POST /query`, `GET /documents`, `GET /documents/{id}`. Não fala direto com Milvus/Postgres nem reimplementa retrieval/citações. FastAPI segue como fonte única da verdade; o MCP é apenas mais um cliente (como o Django).
- **App próprio:** `apps/mcp/`, cliente leve com `base_url` da API configurável por ambiente (ex.: `http://localhost:8000`).
- **Tools expostas** (aproveitando a categorização — `doc_type`/`tags`):
  - `search_documents(question, filters?, top_k?)` → resposta + citações;
  - `list_documents(filters?)` e `get_document(id)` → navegar o acervo por categoria/metadado;
  - `retrieve_chunks(question, top_k?)` → apenas trechos relevantes (sem geração), para o agente montar seu próprio prompt.
- **Transporte:** stdio por padrão (integração local com agentes); HTTP/SSE configurável.
- **Auth:** POC local sem autenticação; controle de acesso fica como evolução futura.

## Impacto

- Nova feature `FEAT-MCP-001` e app `apps/mcp/` (ADR-0003 atualizado).
- O MCP reusa os contratos `query-and-citations` e `upload-and-metadata`; mudança neles afeta o MCP.
- Grounding e citações vêm prontos da API — o agente consumidor recebe respostas rastreáveis.

## Alternativas rejeitadas

- **MCP importando o domínio direto**: acoplaria o MCP ao processo/deps do backend.
- **MCP acessando Milvus/Postgres diretamente**: duplicaria retrieval, montagem de contexto e citações — fere o guardrail.

## Data

2026-07-09

## Status

aceita
