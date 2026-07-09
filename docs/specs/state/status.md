# Estado operacional — Milvus RAG (POC)

Memória operacional única e enxuta. Substitui a máquina completa de workflow-runs/changelogs do projeto original.

## Trabalho em aberto

| Item | Feature | Etapa atual | Próxima ação | Status |
|---|---|---|---|---|
| WORK-001 | todas | `ops/` criado (compose Podman) | Subir infra (`podman compose up -d`) → esqueleto `apps/api/` (FastAPI + db + Alembic) | aberto |

> Status possíveis: `aberto`, `bloqueado`, `concluido`, `cancelado`, `substituido`.

## Status de implementação

| Feature | status_spec | status_impl |
|---|---|---|
| FEAT-UPLOAD-001 | aprovada (v0.2.0) | nao_iniciada |
| FEAT-INGEST-001 | aprovada (v0.4.0) | nao_iniciada |
| FEAT-QUERY-001 | aprovada (v0.3.0) | nao_iniciada |
| FEAT-MCP-001 | aprovada (v0.1.0) | nao_iniciada |

## Changelog

- 2026-07-09 — **ADR-0006** (parametrização: tudo por env, config única, POC local → gerenciados). Persistência dos containers migrada de volumes nomeados para **bind mounts no projeto** (`data/volumes/`, via `DATA_DIR`), separada de `data/uploads/`. Stack recriada e validada (todos healthy, dados gravando em `data/volumes/`). ADR-0003, backend-api, ops/README e .gitignore atualizados.
- 2026-07-09 — **ADR-0004** (ingestão assíncrona: worker daemon + fila `ingestion_job` no Postgres, embeddings em lote) e **ADR-0005** (MCP como cliente HTTP da API). Nova feature **FEAT-MCP-001**; FEAT-INGEST-001 → v0.4.0 (worker). Estrutura (ADR-0003) ganhou `apps/api/app/worker.py` e `apps/mcp/`; arquitetura e overview propagados.
- 2026-07-09 — **ADR-0003** (estrutura de diretórios: apps/api domínio, apps/web cliente, Alembic/SQLAlchemy, data/uploads). **`ops/` criado**: `docker-compose.yml` (Postgres + Milvus + etcd + minio) com volumes nomeados persistentes, `.env.example` e README com comandos Podman.
- 2026-07-09 — **ADR-0002 revisado**: embeddings migrados para `embeddinggemma-300m` (768, COSINE) servido pelo LM Studio (`/v1/embeddings`); backend deixa de usar `sentence-transformers`. **Postgres + Milvus** passam a subir juntos em containers (runtime **Podman**) via `compose` em `ops/`. Features INGEST/QUERY → v0.3.0; vector-index, arquitetura e overview propagados.
- 2026-07-09 — WORK-001 aberto. Stack decidida e registrada em **ADR-0002** (embeddings locais `bge-m3` 1024/COSINE, geração via LM Studio, formatos PDF/DOCX/TXT-MD/HTML/.py/XLS, Milvus standalone Docker). `vector-index.md` fixado; features migradas para **v0.2.0** e `status_spec: aprovada`; overview, contratos e arquitetura propagados.
- 2026-07-09 — Templates `features/_TEMPLATE.md` e `decisions/_TEMPLATE-ADR.md` criados; 3 features migradas para o template completo (v0.1.0) com Histórico de atualizações próprio.
- 2026-07-09 — Estrutura inicial de specs da POC criada (produto, arquitetura, contratos, features, testes, ADR-0001).

## Lacunas conhecidas

- Calibrar tamanho/overlap de chunking por família de formato (default definido; ajustar após avaliação de retrieval) — FEAT-INGEST-001.
- Calibrar limiar de similaridade COSINE para "sem contexto suficiente" — FEAT-QUERY-001.
- Definir limite máximo de tamanho de upload — FEAT-UPLOAD-001.
- Decidir se `query_log` entra na POC (auditoria/avaliação) — FEAT-QUERY-001.
- Estrutura de código (`apps/web/`, `apps/api/`, `ops/`) ainda não criada.

## Mapa de integração

- Django (`apps/web/`) → FastAPI (`apps/api/`): contratos `upload-and-metadata`, `query-and-citations`.
- FastAPI → PostgreSQL: `document`, `chunk`, `ingestion_job`, `query_log?`.
- FastAPI → Milvus: coleção de vetores (`vector[768]` + `chunk_id` + payload de metadados). Container (`ops/`, Podman).
- FastAPI → PostgreSQL: container (`ops/`, Podman).
- FastAPI → LM Studio (API OpenAI-compatível, `base_url` configurável): embeddings `embeddinggemma-300m` (`/v1/embeddings`) e geração (`/v1/chat/completions`).
- Worker (`apps/api/app/worker.py`) → fila `ingestion_job` (Postgres) + LM Studio (embeddings em lote) + Milvus (indexação).
- MCP (`apps/mcp/`) → API FastAPI (`POST /query`, `GET /documents[...]`) como cliente HTTP.
