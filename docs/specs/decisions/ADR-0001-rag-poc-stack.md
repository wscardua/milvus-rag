# ADR-0001 — Stack da POC de RAG

## Contexto

POC de RAG sobre documentos submetidos, com UI de carga/metadados e consulta com citações.

## Decisão

- **UI**: Django (`apps/web/`) — upload, metadados, listagem, consulta, admin.
- **Domínio/API**: FastAPI (`apps/api/`) — ingestão, chunking, embeddings, retrieval, geração.
- **Metadados/estado**: PostgreSQL.
- **Índice vetorial**: Milvus.

Django é cliente; FastAPI é a fonte da verdade. Cada vetor no Milvus referencia um chunk rastreável no Postgres.

## Impacto

- Modelo/dimensão/métrica de embeddings viram contrato do índice (mudança futura = novo ADR + reindexação).
- Fronteiras validadas por `milvus-rag-architecture-guard`.

## Alternativas rejeitadas

- UI só em API (sem Django): descartada — a carga/metadados é feita em Django.
- pgvector no lugar do Milvus: fora do escopo desta POC (índice dedicado = Milvus).

## Data

2026-07-09

## Status

aceita
