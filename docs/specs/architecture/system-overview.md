# Arquitetura — Visão geral

## Camadas e responsabilidades

| Camada | Local | Responsabilidade |
|---|---|---|
| Web (Django) | `apps/web/` | Upload, metadados, listagem, consulta (+feedback), exclusão/visualização/download de documentos, admin, **Logs & Saúde**. Cliente da API. |
| MCP (servidor) | `apps/mcp/` | Consulta ao acervo para outros agentes. Cliente HTTP da API (ADR-0005). |
| API/Domínio (FastAPI) | `apps/api/` | Ingestão, chunking, embeddings, retrieval, geração com citações. Fonte da verdade. |
| Worker (ingestão) | `apps/api/` (`app/worker.py`) | Daemon assíncrono que consome a fila `ingestion_job` (ADR-0004). |
| Banco (PostgreSQL) | container | Documentos, chunks, metadados, estado/fila de ingestão, auditoria. |
| Índice (Milvus) | container | Busca por similaridade. |
| Embeddings + LLM | LM Studio | Servidor local, API OpenAI-compatível: `embeddinggemma-300m` (768, COSINE) em `/v1/embeddings` e chat em `/v1/chat/completions`. |
| Ops | `ops/` | `compose` de Postgres + Milvus (runtime Podman), scripts, deploy local. |

Stack decidida em [ADR-0001](../decisions/ADR-0001-rag-poc-stack.md) e [ADR-0002](../decisions/ADR-0002-embeddings-llm-and-runtime.md). Embeddings e geração rodam **localmente no LM Studio**; Postgres e Milvus sobem em **containers (Podman/Docker)**. Nenhum conteúdo sai do ambiente.

## Fluxo de dados

```
INGESTÃO (assíncrona)
Upload (Django) → API POST /documents → cria ingestion_job=pending (responde na hora)
   Worker daemon → reivindica job → extração → chunking
      → embeddings em lote (LM Studio /v1/embeddings)
      → Milvus (vetores) + Postgres (chunks/estado)

CONSULTA
Django  ─┐
MCP     ─┼→ API POST /query (FastAPI)
(agente) ┘   → embedding da pergunta → busca top-k no Milvus (+ filtros)
             → chunks do Postgres → montagem de contexto → geração (LM Studio)
             → resposta + citações
```

## Fronteiras (guardrails)

- Django e MCP são clientes — não fazem chunking/embeddings/retrieval, nem leem Postgres/Milvus/arquivos direto (acesso a arquivo e logs é via API; Django faz proxy — ADR-0010/0011).
- A API é a única fonte de retrieval/geração; o worker é a única fonte de ingestão.
- Cada vetor no Milvus referencia um chunk rastreável no Postgres. **Excluir um documento remove seus chunks e vetores** (sem órfãos — ADR-0010).
- Modelo/dimensão/métrica de embeddings são contrato do índice (mudança = ADR + reindexação).
