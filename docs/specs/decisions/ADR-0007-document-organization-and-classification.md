# ADR-0007 — Organização por Squad/Processo e classificação de documentos

## Contexto

A POC passou a ter uma exigência de negócio: cada documento pertence a um **processo de delivery**, que por sua vez pertence a uma **squad** (`Squad → Processo de Delivery → Documento`). Além disso, o produto quer **classificar** cada documento por `category`/`subcategory` (taxonomia fixa) e ter um `summary`, com esses três campos **sugeridos por IA durante a ingestão e editáveis pelo usuário**.

O esboço atual de schema ([architecture/database.md](../architecture/database.md)) tem apenas `document`/`chunk`/`ingestion_job`/`query_log?`, sem organização hierárquica nem campos classificatórios. Isso é uma **mudança de schema estrutural** (gatilho de ADR) e afeta os campos filtráveis do índice Milvus.

## Decisão

### Novas tabelas de organização
- **`squad`**: `id`, `name` (unique), `description`, timestamps.
- **`delivery_process`**: `id`, `squad_id` (FK → `squad`, `ON DELETE RESTRICT`), `name`, `description`, timestamps, **unique (`squad_id`, `name`)**.

### Taxonomia como tabelas de referência (não ENUM nativo)
- **`category`**: `id`, `name` (unique).
- **`subcategory`**: `id`, `category_id` (FK → `category`), `name`, **unique (`category_id`, `name`)**.
- Motivo: a subcategoria depende da categoria (selects dependentes na UI) e a lista pode crescer sem `ALTER TYPE`/migration de tipo.
- **Listas iniciais (seed):** ver [reference/taxonomy.md](../reference/taxonomy.md) — fonte da verdade das categorias/subcategorias e do enum `doc_type`.

### Extensão de `document`
- `delivery_process_id` (FK → `delivery_process`, **NOT NULL**, `ON DELETE RESTRICT`). A squad é derivada por join — **não** se duplica `squad_id` na `document`.
- `title` (text): **opcional no upload**; se vazio, sugerido pela IA na ingestão (fallback = nome do arquivo), editável pelo usuário. Integra o conjunto sugerido-pela-IA.
- `category_id` (FK → `category`, nullable), `subcategory_id` (FK → `subcategory`, nullable): **sugeridos pela IA na ingestão, editáveis pelo usuário**.
- `summary` (text, nullable): idem.
- `classification_source` (`llm` | `user`): rastreia se houve override do usuário nos campos sugeridos (`title`/`category`/`subcategory`/`summary`).
- `ingested_at` (timestamptz, nullable): preenchido quando o documento atinge `indexed`.
- `tags` permanece **`text[]`** (com índice GIN), conforme esboço atual.

### Reflexo no índice Milvus
- O payload filtrável ganha `squad_id`, `delivery_process_id`, `category`, `subcategory` (além de `document_id`, `chunk_id`, `doc_type`, `tags`, `author`), para suportar os filtros de retrieval por squad/processo/categoria.

### Integridade
- Exclusão de `squad`/`delivery_process` com documentos vinculados é **bloqueada** (`ON DELETE RESTRICT`), preservando a rastreabilidade das citações.

## Impacto

- **FEAT-WEB-001** (frontend): habilita as telas de admin (Squads/Processos), o vínculo obrigatório no upload, a edição da classificação sugerida e os filtros de consulta por squad/processo.
- **FEAT-INGEST-001**: ganha um passo de **classificação por IA** (sugerir `category`/`subcategory` dentro da taxonomia + `summary`), tratando o conteúdo como entrada não confiável (mitigar prompt injection). Bump de versão.
- **Contratos**: `upload-and-metadata` (input com `delivery_process_id`; `PATCH /documents/{id}` para overrides de classificação); `query-and-citations` (filtros `squad`/`delivery_process`); novo contrato de **admin de organização** (CRUD de squad/processo + leitura de taxonomia).
- **architecture/database.md** e **architecture/vector-index.md**: atualizados com as tabelas, colunas e payload.
- **Migrations (Alembic)**: novas tabelas + colunas em `document`. Como ainda **não há dados/coleção Milvus criados**, **não há reindexação** de acervo existente — o contrato do índice (modelo/dimensão/métrica, ADR-0002) permanece imutável; apenas o payload de metadados filtráveis é ampliado.

## Alternativas rejeitadas

- **ENUM nativo do Postgres para categoria/subcategoria**: rígido; alterar a lista exige `ALTER TYPE`; não modela bem a dependência subcategoria→categoria. Rejeitado em favor de tabelas de referência.
- **Duplicar `squad_id` em `document`**: desnormalização redundante (a squad já vem pelo processo); risco de inconsistência. Rejeitado — squad via join. (Payload do Milvus carrega `squad_id` denormalizado apenas para filtro rápido no índice, resolvido na indexação.)
- **Tabela de tags normalizada (N:N)**: mais estrutura do que a POC precisa; `text[]` + GIN atende. Reavaliar se houver necessidade de renomear/deduplicar tags.
- **Soft delete de squad/processo**: mantém histórico, mas adiciona complexidade de filtragem; para a POC, `RESTRICT` é suficiente e mais seguro.

## Data

2026-07-09

## Status

aceita
