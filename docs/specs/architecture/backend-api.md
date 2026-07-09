# Arquitetura — Backend API (FastAPI)

Runtime em `apps/api/`. Fonte da verdade do domínio de RAG.

## Responsabilidades

- Receber upload e metadados; validar tipo/tamanho e **enfileirar** ingestão (`ingestion_job=pending`), respondendo na hora.
- Expor estado de ingestão por documento.
- Atender consultas: retrieval + geração com citações (consumido por Django e pelo MCP).
- Erros consistentes e auditáveis.

O **pipeline de ingestão** roda no **worker daemon** (`app/worker.py`), não no request — ver ADR-0004 e FEAT-INGEST-001. Domínio (`domain/ingestion`, `domain/retrieval`), integrações (`services/`) e `db/` são compartilhados entre API e worker.

## Serviços internos e integrações

O backend é um **cliente leve**: embeddings e geração vêm do LM Studio; não há modelo de ML carregado no processo.

- **Embeddings (LM Studio):** `embeddinggemma-300m` via `/v1/embeddings` (OpenAI-compatível). Dimensão 768, métrica COSINE, contexto 2048. Usado na ingestão e na consulta.
- **LLM (LM Studio):** geração via `/v1/chat/completions`. Mesmo `base_url`; modelo de chat e embedding ficam carregados simultaneamente no LM Studio.
- **Milvus:** cliente `pymilvus`; host/porta configuráveis (container em `ops/`).
- **PostgreSQL:** container em `ops/`; conexão configurável.
- **Extração por formato:** PDF, DOCX, TXT/MD, HTML, `.py`, XLS/XLSX (ver ADR-0002 para a estratégia por família).
- Todas as integrações são **configuráveis por ambiente** (`base_url` do LM Studio, hosts de Postgres/Milvus); tudo roda localmente.

## Configuração (ADR-0006)

Nada de endpoint/credencial/modelo hardcoded. Um `Settings` (Pydantic `BaseSettings`) em `app/config.py` é o ponto único de configuração; o código recebe config injetada. Parâmetros principais: `DATABASE_URL`, `MILVUS_URI`/`MILVUS_HOST`/`MILVUS_PORT`/`MILVUS_TOKEN?`, `MILVUS_COLLECTION`/`EMBEDDING_DIM`/`MILVUS_METRIC`, `EMBEDDINGS_BASE_URL`/`EMBEDDINGS_MODEL`/`EMBEDDINGS_API_KEY?`, `LLM_BASE_URL`/`LLM_MODEL`/`LLM_API_KEY?`, `UPLOAD_DIR`, `CHUNK_SIZE`/`CHUNK_OVERLAP`/`INGEST_BATCH_SIZE`, `DEFAULT_TOP_K`/`SIMILARITY_THRESHOLD`. Como embeddings/LLM usam API OpenAI-compatível, migrar para serviços gerenciados é troca de `.env`.

## Endpoints (esboço)

- `POST /documents` — upload + metadados; dispara ingestão (idempotente).
- `GET /documents/{id}` — estado de ingestão e metadados.
- `GET /documents` — listagem com filtros por metadado.
- `GET /documents/{id}/file` — arquivo original (inline/attachment; ADR-0010).
- `DELETE /documents/{id}` — exclusão em cascade + Milvus + arquivo (ADR-0010).
- `POST /query` — pergunta → resposta + citações + `query_id`.
- `POST /retrieve` — retrieval puro (sem geração): apenas trechos relevantes + score. Consumido pela tool `retrieve_chunks` do MCP (ADR-0005); não grava `query_log`.
- `POST /query/{query_id}/feedback` — 👍/👎 da resposta (ADR-0011).
- `GET /health` — saúde por serviço (Postgres/Milvus/LM Studio/worker) + fila (ADR-0011).
- `GET /logs` — eventos do `system_log` com filtros (ADR-0011).

## Regras

- Serviços de domínio concentram ingestão e retrieval; endpoints são finos.
- Toda resposta gerada carrega citações (chunk + documento).
- Conteúdo submetido é entrada não confiável (mitigar prompt injection).
