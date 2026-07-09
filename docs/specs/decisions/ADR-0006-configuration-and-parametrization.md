# ADR-0006 — Parametrização e estratégia de configuração

## Contexto

A POC roda 100% local (Postgres/Milvus em containers, embeddings e LLM no LM Studio), mas precisa prever a migração futura para **serviços gerenciados** (ex.: Postgres gerenciado, Milvus/Zilliz Cloud, LLM/embeddings via API na nuvem) sem reescrever código. Endereços, credenciais e modelos não podem estar hardcoded.

## Decisão

- **Tudo configurável por ambiente.** Nenhum endpoint, credencial, porta, caminho ou nome de modelo fixo no código. Valores vêm de variáveis de ambiente, com defaults sensatos para o setup local.
- **Camada de config única por app.** No FastAPI, um `Settings` (Pydantic `BaseSettings`) em `app/config.py` centraliza a leitura do ambiente; o resto do código recebe config injetada, nunca lê `os.environ` espalhado. Django e MCP seguem o mesmo princípio.
- **`.env` por app** (`apps/api/.env`, `apps/web/.env`, `apps/mcp/.env`) + `.env.example` versionado. `ops/.env` para a infra. Todos os `.env` reais são gitignored.
- **Parâmetros mínimos previstos:**

| Domínio | Variáveis (exemplo) | Local → Gerenciado |
|---|---|---|
| PostgreSQL | `DATABASE_URL` | container local → instância gerenciada |
| Milvus | `MILVUS_HOST`, `MILVUS_PORT`, `MILVUS_URI`, `MILVUS_TOKEN?` | `localhost:19530` → endpoint/token Zilliz Cloud |
| Coleção | `MILVUS_COLLECTION`, `EMBEDDING_DIM`, `MILVUS_METRIC` | 768 / COSINE (contrato do índice, ADR-0002) |
| Embeddings | `EMBEDDINGS_BASE_URL`, `EMBEDDINGS_MODEL`, `EMBEDDINGS_API_KEY?` | LM Studio `/v1` → provedor gerenciado |
| LLM | `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY?` | LM Studio `/v1` → provedor gerenciado |
| Upload/ingestão | `MAX_UPLOAD_MB`, `CHUNK_SIZE`, `CHUNK_OVERLAP`, `INGEST_BATCH_SIZE` | tuning local |
| Retrieval | `DEFAULT_TOP_K`, `SIMILARITY_THRESHOLD` | tuning local |
| MCP | `API_BASE_URL`, `MCP_TRANSPORT` | aponta para a API FastAPI |
| Storage de arquivos | `UPLOAD_DIR` | `data/uploads` → bucket/objeto gerenciado (futuro) |
| Infra (ops) | `DATA_DIR`, portas, versões, credenciais | bind mount local → irrelevante em gerenciado |

- Como embeddings e LLM já usam **API OpenAI-compatível**, trocar para um provedor gerenciado é só mudar `*_BASE_URL`, `*_API_KEY` e `*_MODEL`.
- Mudança de dimensão/métrica de embeddings continua sendo **contrato do índice** (ADR-0002): parametrizável, mas alterá-la exige reindexação.

## Impacto

- `apps/api/app/config.py` é o ponto único de verdade de configuração do backend.
- Cada `.env.example` documenta o catálogo de variáveis do seu app.
- Migração para gerenciados vira mudança de `.env`, sem alteração de código.
- Persistência local parametrizada por `DATA_DIR` (bind mounts em `data/volumes/`).

## Alternativas rejeitadas

- **Endpoints/credenciais hardcoded** com "trocar depois": gera dívida e risco de vazar segredo em commit.
- **Config dispersa (`os.environ` por todo lado)**: difícil de auditar e testar; sem defaults coerentes.

## Data

2026-07-09

## Status

aceita
