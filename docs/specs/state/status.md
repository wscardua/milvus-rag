# Estado operacional — Milvus RAG (POC)

Memória operacional única e enxuta. Substitui a máquina completa de workflow-runs/changelogs do projeto original.

## Trabalho em aberto

| Item | Feature | Etapa atual | Próxima ação | Status |
|---|---|---|---|---|
| WORK-001 | todas | Infra up; `apps/api/` com camada de dados (SQLAlchemy + Alembic) criada e migrada | Esqueleto FastAPI (`main.py`, routers, schemas, services) | aberto |
| WORK-002 | FEAT-WEB-001 | **POC RAG funcional ponta a ponta**: dados + API (org/upload/links/query) + worker (ingestão/classificação/retry) + frontend Django. Testado com LM Studio real (embedding + chat): upload→ingestão→classificação IA→retrieval→resposta com citações→expansão por vínculos→"sem contexto suficiente" | Refino/robustez: heartbeat periódico no worker, avaliação de retrieval, testes automatizados; FEAT-MCP-001 (servidor MCP) | aberto |

> Status possíveis: `aberto`, `bloqueado`, `concluido`, `cancelado`, `substituido`.

## Status de implementação

| Feature | status_spec | status_impl |
|---|---|---|
| FEAT-UPLOAD-001 | aprovada (v0.3.0) | implementada |
| FEAT-INGEST-001 | aprovada (v0.7.0) | implementada |
| FEAT-QUERY-001 | aprovada (v0.4.0) | implementada |
| FEAT-MCP-001 | aprovada (v0.1.0) | nao_iniciada |
| FEAT-WEB-001 | rascunho (v0.3.0) | implementada |

## Changelog

- 2026-07-09 — **PR**: consolidação da POC RAG no branch `feature/frontend-layout` — specs (ADR-0007/0008/0009, contratos, taxonomia, arquitetura), `apps/api` (FastAPI + worker) e `apps/web` (Django). Abre via `/enviar-pr`.
- 2026-07-09 — **Implementação (núcleo RAG — worker + `/query`)**: services `lmstudio`/`embeddings`/`llm`/`vectorstore` (Milvus 768/COSINE/HNSW); `domain/ingestion` (extração PDF/DOCX/HTML/XLSX/txt-md-py, chunking por palavras, classificação IA restrita à taxonomia, pipeline idempotente); `app/worker.py` (claim SKIP LOCKED + retry/backoff + visibility timeout — ADR-0009); `domain/retrieval` + `POST /query` (busca vetorial c/ filtros + expansão de 1 salto por vínculos + geração com citações + `linked_flow` + limiar "sem contexto suficiente"). **Testado com LM Studio real** (`text-embedding-embeddinggemma-300m` + `gemma-3-4b-it-qat`): upload→indexação→classificação (título/categoria/resumo via IA)→consulta com resposta ancorada e citação; expansão trouxe definição de doc vinculado; pergunta fora do acervo → insufficient_context. Consulta Django renderiza resposta/citações/fluxo. FEAT-UPLOAD/INGEST/QUERY/WEB → status_impl `implementada`. (setuptools pinado <81 p/ pymilvus.)
- 2026-07-09 — **Implementação (Frontend Django)**: criado `apps/web/` (Django 5.1, cliente HTTP da API — sessão/mensagens por cookie, sem banco de domínio, guardrail respeitado). Cliente `core/client.py`; views `organization` (Squads/Processos CRUD), `documents` (listagem c/ filtros, upload multipart, detalhe c/ edição de classificação + selects dependentes + vínculos/fluxo), `query` (shell tolerante ao `/query` ausente). Layout Carbon (`static/css/app.css`, `templates/base.html` + 6 páginas). API ganhou `/doc-types` e `/link-types`. Testado ponta a ponta pela UI (squad→processo→upload→listagem→detalhe→PATCH override; consulta sinaliza `/query` indisponível). Comandos em CLAUDE.md.
- 2026-07-09 — **Implementação (API parte 1)**: `apps/api/app/` ganhou `main.py` (FastAPI + `/health`), `schemas/` (Pydantic = contratos), `services/storage.py` e routers `organization.py` (CRUD squad/processo + taxonomia), `documents.py` (upload enfileira `ingestion_job`, listagem c/ filtros, detalhe, `PATCH` de overrides → `classification_source=user`) e `links.py` (vínculos tipados, validação de mesma squad). Testado ponta a ponta via HTTP (happy path + 422 mesma-squad/doc_type, 409 RESTRICT/duplicado, 415 extensão). `query`/services/worker pendentes.
- 2026-07-09 — **Implementação (camada de dados)**: criado `apps/api/` (ADR-0003) com `config.py` (pydantic-settings, ADR-0006), `db/models.py` (squad, delivery_process, category, subcategory, document, document_link, chunk, ingestion_job), Alembic (migration inicial `78d0b3b785b3`) aplicada no Postgres do `ops/`, e seed idempotente da taxonomia (`app.db.seed_taxonomy` — 7 categorias/30 subcategorias). Deps instaladas no `venv/` (`apps/api/requirements.txt`).
- 2026-07-09 — Taxonomia: novo `doc_type` **"Base de Conhecimento"** (`reference/taxonomy.md` + mock).
- 2026-07-09 — **ADR-0009** (retry/visibility-timeout do worker): política de tolerância a falhas do daemon de ingestão — heartbeat + recuperação de jobs presos em `processing` (embutida na query de claim), retry com backoff exponencial para falhas transitórias (`WORKER_MAX_ATTEMPTS` default 3; timeout default 5min), `failed` imediato para falhas permanentes. `ingestion_job` ganha `attempts`/`started_at`/`heartbeat_at`/`available_at`. FEAT-INGEST-001 → v0.7.0; `database.md` propagado. Complementa ADR-0004.
- 2026-07-09 — **ADR-0008** (vínculos entre documentos + expansão de retrieval): tabela `document_link` (auto-relação direcionada e tipada — `esclarece`/`complementa`/`precede`/`substitui` — restrita à mesma squad); retrieval faz expansão de **1 salto** (inclui esclarece/complementa/precede, exclui `substitui` obsoleto) e a resposta traz `linked_flow[]`. Novo contrato `document-links`; `query-and-citations` +`linked_flow`. **ADR-0007 ajustado**: `title` entra no conjunto sugerido-pela-IA e vira **opcional** no upload. Bumps: FEAT-UPLOAD-001 → v0.3.0, FEAT-INGEST-001 → v0.6.0, FEAT-QUERY-001 → v0.4.0, FEAT-WEB-001 → v0.3.0. Propagado em `database.md`, `taxonomy.md` (tipos de vínculo), contratos e mock.
- 2026-07-09 — **Taxonomia definida**: `reference/taxonomy.md` criado (fonte da verdade) — 7 categorias × 4 subcategorias + 11 `doc_type`. Vira seed de `category`/`subcategory` e lista fechada da classificação por IA. Ligado em ADR-0007, FEAT-INGEST-001 e FEAT-WEB-001.
- 2026-07-09 — **ADR-0007** (organização Squad/Processo + classificação): novas tabelas `squad`, `delivery_process`, `category`, `subcategory`; `document` ganha `delivery_process_id` (NOT NULL, RESTRICT), `category_id`/`subcategory_id`/`summary`/`classification_source`/`ingested_at`; payload Milvus += `squad_id`/`delivery_process_id`/`category`/`subcategory`. Propagado em `database.md`, `vector-index.md`, contratos (`upload-and-metadata` +`PATCH`, `query-and-citations` +filtros, novo `organization-admin`). **FEAT-INGEST-001 → v0.5.0** (passo de classificação por IA). FEAT-WEB-001 → v0.2.0.
- 2026-07-09 — **WORK-002 aberto**: nova feature **FEAT-WEB-001** (Layout do Frontend, UI Django) — 6 telas no IBM Carbon Design System (Documentos, Upload, Detalhe, Consulta, Squads, Processos). Introduz modelo **Squad → Processo de Delivery → Documento** e classificação **sugerida por IA e editável** (`category`/`subcategory`/`summary`). Spec `frontend-layout.md` (rascunho v0.1.0) e mock estático em `mocks/frontend-layout.html` criados. Depende de: ADR de schema (a abrir), extensão de contratos e bump de FEAT-INGEST-001.
- 2026-07-09 — `/enviar-pr` refatorado para **gate único de autorização**: resumo antes de alterar qualquer coisa e uma aprovação que cobre todos os passos até o merge (sem re-confirmar); trava de segurança mantida para achados críticos no review.
- 2026-07-09 — Adicionado slash command `/enviar-pr` (`.claude/commands/`): orquestra o fluxo de PR (sync → atualizar specs/docs → branch/commit → PR → review → merge → sync), derivando a descrição do diff quando não informada.
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
- Definir o **prompt de classificação/resumo** que restringe a saída da IA à taxonomia (`reference/taxonomy.md`) — FEAT-INGEST-001.
- Detalhar payloads/erros dos contratos estendidos na implementação (`organization-admin`, `PATCH` de overrides).
- **Achados de review (PR #4) — follow-ups não críticos (POC):**
  - Worker: heartbeat não é renovado durante o processamento (só no claim); doc que leve > `WORKER_VISIBILITY_TIMEOUT` pode ser reivindicado em paralelo. Implementar heartbeat periódico (thread/tick). Pipeline é idempotente, então o risco é retrabalho, não corrupção.
  - Upload via API com `links[]` inválidos: `IntegrityError`/`ValidationError` no commit não são tratados → 500 + arquivo órfão em `data/uploads/`. Envolver em try/except e limpar o arquivo. (A UI não envia `links` no upload.)
  - Embeddings enviados num único lote; documentos muito grandes podem exceder o limite do LM Studio. Fatiar em sub-lotes.
  - Consulta (UI): filtro `delivery_process` é suportado pela API mas não há select na tela; adicionar select dependente de squad.
  - UI: erros 422 da API (detail em lista) aparecem como repr cru; formatar mensagem amigável. Detalhe redireciona se qualquer GET secundário falhar (acoplamento); ícone de `warning` usa ℹ️.
  - Reindexação: embora embeddings venham antes do delete, delete(Milvus)+upsert não são transacionais com o Postgres; falha entre eles deixa janela até o próximo retry.

## Mapa de integração

- Django (`apps/web/`) → FastAPI (`apps/api/`): contratos `upload-and-metadata`, `query-and-citations`, `organization-admin`, `document-links`.
- FastAPI → PostgreSQL: `squad`, `delivery_process`, `category`, `subcategory`, `document`, `document_link`, `chunk`, `ingestion_job`, `query_log?`.
- FastAPI → Milvus: coleção de vetores (`vector[768]` + `chunk_id` + payload `document_id`/`doc_type`/`tags`/`author`/`squad_id`/`delivery_process_id`/`category`/`subcategory`). Container (`ops/`, Podman).
- FastAPI → PostgreSQL: container (`ops/`, Podman).
- FastAPI → LM Studio (API OpenAI-compatível, `base_url` configurável): embeddings `embeddinggemma-300m` (`/v1/embeddings`) e geração (`/v1/chat/completions`).
- Worker (`apps/api/app/worker.py`) → fila `ingestion_job` (Postgres) + LM Studio (embeddings em lote) + Milvus (indexação).
- MCP (`apps/mcp/`) → API FastAPI (`POST /query`, `GET /documents[...]`) como cliente HTTP.
