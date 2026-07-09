# Arquitetura — Banco (PostgreSQL)

Persiste metadados, chunks e estado; não substitui o domínio.

## Entidades (esboço)

- `document` — arquivo + metadados (título, autor, tags, tipo, timestamps).
- `chunk` — texto do trecho, posição/ordem, FK para `document`, id do vetor no Milvus.
- `ingestion_job` — estado (`pending`/`processing`/`indexed`/`failed`), erro, timestamps.
- `query_log` (opcional) — pergunta, chunks recuperados, citações retornadas (auditoria).

## Regras

- Cada `chunk` é rastreável até seu `document` e ao vetor no Milvus (citações).
- Estado de ingestão permite reprocessamento idempotente.
- Índices por documento, por estado de job e por metadado filtrável.
