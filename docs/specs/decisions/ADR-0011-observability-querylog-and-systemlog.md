# ADR-0011 — Observabilidade: query_log, system_log e health por serviço

## Contexto

A POC não tinha como (a) **avaliar a qualidade das respostas** para azeitar modelo/chunking/retrieval, nem (b) **fazer troubleshooting** do que acontece na ingestão/consulta, nem (c) **ver a saúde** dos serviços/daemons. O negócio pediu um "joinha" (👍/👎) na consulta e uma página de logs com a saúde do sistema. `query_log` já figurava como lacuna nas specs (FEAT-QUERY-001, database.md) sem colunas nem ADR. Formalizar isso é **mudança de schema estrutural** (novas tabelas) → gatilho de ADR.

## Decisão

### `query_log` — auditoria de consulta + feedback (formaliza a lacuna)
- **Toda** chamada a `POST /query` grava uma linha, não só quando há voto. Guarda pergunta, filtros, `top_k`, `insufficient_context`, resposta, citações e `linked_flow` (JSONB), além de métricas para tuning: `scores[]`, `retrieved_chunk_ids[]`, `retrieved_document_ids[]`, `embedding_model`, `chat_model`, `chunk_size_words`, `chunk_overlap_words`, `retrieval_min_score`, `latency_ms`.
- `POST /query` passa a devolver `query_id` (id do `query_log`). O feedback usa esse id: `POST /query/{query_id}/feedback` com `{rating: "up"|"down"}` grava `rating` (1/-1) e `rating_at`.
- **Sem FK** para `document`/`chunk`: os ids são snapshot em JSONB, para o histórico de avaliação sobreviver à exclusão de documentos (ADR-0010).

### `system_log` — log de eventos no Postgres
- Tabela com `ts`, `level` (INFO/WARN/ERROR), `component` (api/worker/ingestion/retrieval), `event`, `message`, `context` (JSONB), `document_id?`, `job_id?`.
- API e worker gravam via helper `log_event(...)` que usa **sessão própria e curta** (isolada da transação do chamador) e é **best-effort**: falhar ao logar nunca derruba o fluxo principal.
- Pontos instrumentados na POC: worker (`worker_started`, `worker_heartbeat`, `job_indexed`, `job_retry`, `job_failed`, `worker_loop_error`), API (`document_deleted`), retrieval (`query_failed`).

### `GET /health` detalhado + `GET /logs`
- `/health` deixa de ser stub e passa a checar por serviço: **Postgres** (`SELECT 1`), **Milvus** (has_collection), **LM Studio** (`/v1/models`), **worker** (liveness derivada: último `worker_heartbeat` recente no `system_log` + ausência de jobs presos). Retorna `{status, components[], queue{por estado}}`. `status = ok` se todos ok, senão `degraded`.
- `/logs` lista `system_log` (mais recentes primeiro) com filtros `level`/`component`/`since`/`limit`.
- Novo contrato **logs-and-health**. A UI Django ganha a tela **Logs & Saúde** (7ª tela), consumindo esses dois endpoints como cliente.

### Worker heartbeat leve
- O loop do worker grava `worker_heartbeat` no `system_log` no máximo 1×/`worker_heartbeat_interval`, dando sinal de vida real para o `/health`. (O heartbeat *periódico durante o processamento de um job* — renovação de `ingestion_job.heartbeat_at` — segue como follow-up, ADR-0009.)

## Impacto

- **FEAT-QUERY-001**: `query_log` + feedback + `query_id` no contrato (bump). Fecha a lacuna "definir se query_log entra na POC" (entra).
- **FEAT-WEB-001**: joinha na Consulta + nova tela Logs & Saúde (bump).
- **FEAT-INGEST-001**: worker emite eventos no `system_log` (bump).
- **Contratos**: `query-and-citations` ganha `query_id` e o endpoint de feedback; novo `logs-and-health`.
- **architecture/database.md**: `query_log` com colunas + nova `system_log`. **backend-api.md**: `/health` detalhado, `/logs`, feedback. **system-overview.md**: 7ª tela; Postgres reforça o papel de "auditoria".
- **Custo**: uma escrita por consulta (`query_log`) e escritas esparsas de eventos; `system_log` cresce — na POC sem retenção/rotação (lacuna registrada).

## Alternativas rejeitadas

- **Só registrar consulta quando há voto**: perde as consultas sem feedback (a maioria) e o material de tuning (scores/latency por pergunta). Rejeitado — loga toda consulta.
- **Handler de logging Python gravando no banco**: acopla o `logging` a uma sessão de DB e complica o controle transacional/erros. Rejeitado — chamadas explícitas de `log_event` com sessão própria.
- **Derivar a página de logs só de `ingestion_job`/`query_log`** (sem `system_log`): não cobre eventos gerais (exclusões, falhas de retrieval, vida do worker) — troubleshooting fraco. Rejeitado — tabela dedicada.
- **Health como stub `{"status":"ok"}`**: não diz nada sobre PG/Milvus/LLM/worker. Rejeitado — checagem por serviço.
- **Tabela de heartbeat do worker dedicada**: overkill na POC; `system_log` + evento `worker_heartbeat` já dá o sinal. Rejeitado por ora.

## Data

2026-07-09

## Status

aceita
