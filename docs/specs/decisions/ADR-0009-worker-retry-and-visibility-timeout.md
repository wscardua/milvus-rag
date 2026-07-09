# ADR-0009 — Retry, visibility timeout e recuperação do worker de ingestão

> Complementa (não substitui) o [ADR-0004](ADR-0004-async-ingestion-worker.md), detalhando a política de tolerância a falhas do daemon.

## Contexto

O ADR-0004 definiu o worker como daemon que reivindica jobs `pending` com `SELECT … FOR UPDATE SKIP LOCKED` e marca `processing → indexed/failed`. Faltou definir o que acontece quando:
- o worker **cai no meio** de um job (fica preso em `processing` para sempre);
- ocorre uma **falha transitória** (LM Studio/Milvus indisponível, timeout de rede) que valeria repetir;
- ocorre uma **falha permanente** (arquivo corrompido, formato não extraível) que não deve ser repetida em loop.

Sem isso, um crash trava o documento e uma falha transitória vira `failed` definitivo indevidamente.

## Decisão

### Campos adicionais em `ingestion_job`
- `attempts` (int, default 0) — nº de reivindicações já feitas.
- `started_at` (timestamptz) — quando entrou em `processing` na tentativa atual.
- `heartbeat_at` (timestamptz) — atualizado periodicamente pelo worker enquanto processa.
- `available_at` (timestamptz, default now()) — job só é elegível quando `now() >= available_at` (usado para backoff).
- `error` (text) — última mensagem de erro (já previsto).

Estados permanecem `pending`/`processing`/`indexed`/`failed`. `pending` é o estado **elegível para (re)tentativa**; `indexed` e `failed` são **terminais**.

### Reivindicação (claim) com recuperação embutida
A query de claim reivindica tanto jobs pendentes quanto **jobs presos** — sem processo reaper separado:

```sql
BEGIN
SELECT * FROM ingestion_job
 WHERE (state = 'pending' AND available_at <= now())
    OR (state = 'processing' AND heartbeat_at < now() - :visibility_timeout)   -- job abandonado
 ORDER BY available_at
 FOR UPDATE SKIP LOCKED
 LIMIT 1
UPDATE ... SET state='processing', started_at=now(), heartbeat_at=now(), attempts = attempts + 1
COMMIT
```

- **Heartbeat:** durante o processamento (ex.: embeddings em lote), o worker atualiza `heartbeat_at` a cada `WORKER_HEARTBEAT_INTERVAL` (default 30s).
- **Visibility timeout:** um job em `processing` cujo `heartbeat_at` esteja mais velho que `WORKER_VISIBILITY_TIMEOUT` (default 5 min) é considerado abandonado e volta a ser reivindicável. Como o pipeline é **idempotente** (ADR-0004), reprocessar é seguro.

### Retry com backoff exponencial
- **Falha transitória** → `state='pending'`, `available_at = now() + backoff(attempts)`, mantém `error`. Backoff exponencial: `WORKER_RETRY_BACKOFF_BASE` × 2^(attempts-1), com teto — default **60s → 300s → 900s**.
- Ao atingir `attempts >= WORKER_MAX_ATTEMPTS` (default **3**) → `state='failed'` (terminal), com `error`.
- **Falha permanente** (validação, extração impossível, tipo/arquivo inválido) → `state='failed'` **imediatamente**, sem retry. O worker classifica o erro (transitório vs permanente) para decidir.

### Reprocessamento manual
Reenfileirar um documento `failed` = criar/resetar o job para `pending` com `attempts=0`, `available_at=now()`. Seguro pela idempotência.

### Configuração (ADR-0006)
Tudo por env: `WORKER_POLL_INTERVAL`, `WORKER_HEARTBEAT_INTERVAL`, `WORKER_VISIBILITY_TIMEOUT`, `WORKER_MAX_ATTEMPTS`, `WORKER_RETRY_BACKOFF_BASE`. Valores default acima; nada hardcoded.

## Impacto

- **FEAT-INGEST-001**: fluxos de erro passam a distinguir transitório/permanente; job ganha `attempts`/`started_at`/`heartbeat_at`/`available_at`. Bump.
- **architecture/database.md**: colunas novas em `ingestion_job` + índice por (`state`, `available_at`).
- **Migrations (Alembic)**: colunas adicionadas a `ingestion_job` (sem dados existentes — POC).
- **Observabilidade:** `attempts` e `error` tornam visível o motivo de um `failed` e quantas vezes tentou (base para a UI e o MCP).
- Sem processo extra: a recuperação de jobs presos é resolvida na própria query de claim.

## Alternativas rejeitadas

- **Reaper/processo separado** varrendo `processing` velhos: mais uma peça para operar; a condição na query de claim resolve com uma linha a mais.
- **Tabela dead-letter dedicada**: `state='failed'` + `attempts` + `error` já cobrem a POC; dead-letter separada é overkill.
- **Retry infinito sem teto**: transformaria falha permanente em loop de custo (LM Studio/Milvus). Rejeitado — `max_attempts`.
- **Sem backoff (retry imediato)**: repetiria contra um serviço já indisponível; backoff exponencial dá tempo de recuperação.
- **Fila externa (Redis/SQS) com visibility timeout nativo**: contraria ADR-0004 (fila = Postgres) e adiciona infra.

## Data

2026-07-09

## Status

aceita
