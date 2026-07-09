# ADR-0004 — Ingestão assíncrona via worker daemon

## Contexto

A ingestão (extração → chunking → embeddings → indexação no Milvus) pode ser demorada: embeddings locais (EmbeddingGemma no LM Studio) processam muitos chunks e documentos grandes (PDF/XLS) geram centenas a milhares de chunks. Fazer isso dentro do request HTTP de upload causaria timeout e travaria a API. A spec já modela `ingestion_job` com estados `pending → processing → indexed/failed`.

## Decisão

- **Upload não processa.** `POST /documents` persiste o `document` e cria um `ingestion_job` com estado `pending`, respondendo imediatamente.
- **Worker daemon separado** consome a fila em Postgres (`ingestion_job`), fora do processo da API:
  - Reivindica jobs `pending` com `SELECT ... FOR UPDATE SKIP LOCKED` (permite N workers em paralelo sem colisão).
  - Marca `processing`, executa o pipeline, marca `indexed` ou `failed` (com erro registrado).
  - **Idempotente:** reprocessar um documento não duplica chunks nem vetores.
- **Embeddings em lote:** o worker envia chunks em batch ao LM Studio (`/v1/embeddings`) para melhorar a vazão.
- **Fila = tabela Postgres** (`ingestion_job`); sem infraestrutura de fila dedicada.
- **Execução:** entrypoint próprio no pacote da API (ex.: `python -m app.worker`), compartilhando `domain/`, `services/` e `db/` com a API.

## Impacto

- FEAT-INGEST-001 passa a descrever explicitamente o worker e o claim da fila.
- Estrutura (ADR-0003) ganha o entrypoint do worker em `apps/api/app/worker.py`.
- Escala horizontal: subir mais workers acelera a ingestão de lotes grandes.
- Observabilidade: estado e erro por job ficam legíveis em `ingestion_job` (base para a UI e o MCP mostrarem progresso).

## Alternativas rejeitadas

- **FastAPI `BackgroundTasks`**: morre com a API, sem retry, disputa recursos com o request.
- **Redis + Celery/RQ/arq**: fila madura, mas adiciona container e dependências — overkill para a POC.
- **Processar no request de upload**: timeout e bloqueio da API.

## Data

2026-07-09

## Status

aceita
