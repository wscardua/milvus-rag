# Arquitetura — Banco (PostgreSQL)

Persiste metadados, chunks e estado; não substitui o domínio.

## Entidades (esboço)

Organização (ADR-0007):
- `squad` — time de delivery (`name` unique, descrição, timestamps).
- `delivery_process` — entrega de uma squad (FK `squad_id` `RESTRICT`; unique `squad_id`+`name`).

Taxonomia (ADR-0007, tabelas de referência — não ENUM nativo):
- `category` — categoria (`name` unique).
- `subcategory` — subcategoria (FK `category_id`; unique `category_id`+`name`).

Núcleo:
- `document` — arquivo + metadados. Vínculo `delivery_process_id` (FK `RESTRICT`, **NOT NULL**; squad vem por join). Metadados do usuário: `author`, `tags text[]`, `doc_type`, dados do arquivo. Campos **sugeridos por IA e editáveis** (ADR-0007): `title` (opcional no upload), `category_id`, `subcategory_id`, `summary`, com `classification_source` (`llm`|`user`). Timestamps + `ingested_at` (quando `indexed`).
- `document_link` (ADR-0008) — auto-relação N:N direcionada e tipada: `source_document_id`, `target_document_id` (FK → `document`), `link_type` (`esclarece`/`complementa`/`precede`/`substitui`), `ordinal`. Restrição: fonte e alvo na **mesma squad**; sem auto-vínculo; unique (`source`,`target`,`link_type`).
- `chunk` — texto do trecho, posição/ordem, FK para `document`, id do vetor no Milvus.
- `ingestion_job` — estado (`pending`/`processing`/`indexed`/`failed`), `error`, timestamps + campos de fila (ADR-0009): `attempts`, `started_at`, `heartbeat_at`, `available_at`.
- `query_log` (opcional) — pergunta, chunks recuperados, citações retornadas (auditoria).

## Regras

- Cada `chunk` é rastreável até seu `document` e ao vetor no Milvus (citações).
- Todo `document` pertence a exatamente um `delivery_process` (e, por herança, a uma `squad`).
- Estado de ingestão permite reprocessamento idempotente; jobs presos em `processing` (heartbeat velho) são recuperados pela query de claim (ADR-0009).
- Exclusão de `squad`/`delivery_process` com documentos vinculados é **bloqueada** (`RESTRICT`) — preserva rastreabilidade das citações.
- `document_link` só relaciona documentos da **mesma squad** (validado na API; ADR-0008). Apagar um documento remove seus vínculos (`CASCADE` em `document_link`).
- `tags` como `text[]` com índice **GIN**; categoria/subcategoria via FK.
- Índices por documento, por `delivery_process`/`squad`, por metadado filtrável, por `document_link` (source/target) e por (`state`, `available_at`) em `ingestion_job` (claim eficiente — ADR-0009).
