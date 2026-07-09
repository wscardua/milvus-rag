# Contrato — Logs e Saúde (Observabilidade)

Entre Django (UI, tela **Logs & Saúde**) e FastAPI (`GET /health`, `GET /logs`). Introduzido pela ADR-0011.

## Saúde — `GET /health`

Resposta:
- `status`: `ok` | `degraded` (`degraded` se qualquer componente estiver fora).
- `components[]`: um por serviço — `name` (`postgres` | `milvus` | `lm_studio` | `worker`), `ok` (bool), `detail` (string).
  - **postgres**: `SELECT 1`.
  - **milvus**: coleção existe/carregada.
  - **lm_studio**: `/v1/models` responde (lista os modelos carregados).
  - **worker**: liveness derivada — último `worker_heartbeat` recente no `system_log` **e** ausência de jobs presos (`processing` com heartbeat além do visibility timeout).
- `queue`: profundidade da fila de ingestão por estado (`pending`, `processing`, `indexed`, `failed`).

## Logs — `GET /logs`

Lista eventos do `system_log`, mais recentes primeiro.
- Filtros (query): `level` (`INFO`|`WARN`|`ERROR`), `component` (`api`|`worker`|`ingestion`|`retrieval`), `since` (ISO), `limit` (default 100, máx 500).
- Cada item: `id`, `ts`, `level`, `component`, `event`, `message`, `context` (objeto), `document_id?`, `job_id?`.

## Regras

- A UI é **cliente**: consome `/health` e `/logs` e apenas renderiza; não checa serviços nem lê o banco direto (guardrail).
- Escrita no `system_log` é responsabilidade da API/worker (helper `log_event`, best-effort) — nunca via UI.
- POC: `system_log` sem retenção/rotação (lacuna conhecida).
