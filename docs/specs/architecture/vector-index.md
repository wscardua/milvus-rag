# Arquitetura — Índice vetorial (Milvus)

Guarda os embeddings e serve busca por similaridade. Deploy **containerizado (Podman/Docker)**, junto do Postgres (ver `ops/`).

## Contrato do índice (ADR-0002)

- **Modelo de embeddings**: `embeddinggemma-300m` (Google, base Gemma 3), servido pelo **LM Studio** (`/v1/embeddings`). Multilíngue (PT-BR incluído).
- **Dimensão do vetor**: `768` (MRL permite 512/256/128; a POC usa 768 cheio).
- **Métrica de similaridade**: `COSINE`.
- **Tipo de índice**: `HNSW` (parâmetros default; ajustáveis conforme volume da POC).
- **Contexto do modelo**: 2048 tokens → chunk deve caber nesse limite.

Estes valores são **contrato**: mudá-los exige novo ADR + **reindexação** de toda a coleção. Não misturar vetores de modelos/dimensões diferentes na mesma coleção. Embeddings rodam **localmente no LM Studio** — nenhum conteúdo sai do ambiente.

## Coleção (esboço)

- `id` — chave primária.
- `vector` — embedding `float[768]`.
- `chunk_id` — referência ao chunk no Postgres (rastreabilidade/citação).
- payload de metadados filtráveis: `document_id`, `doc_type`, `tags`, `author` e, por ADR-0007, `squad_id`, `delivery_process_id`, `category`, `subcategory` (denormalizados na indexação para filtro de retrieval por squad/processo/categoria).

> ADR-0007 amplia **apenas o payload de metadados filtráveis** — modelo/dimensão/métrica (contrato do índice, ADR-0002) permanecem imutáveis; não há reindexação por conta desta mudança.

## Regras

- Todo vetor referencia um chunk rastreável no Postgres.
- **Exclusão de documento (ADR-0010)**: os vetores do documento são removidos por `document_id` (`delete_by_document`) antes de apagar a linha no Postgres — mantém o invariante "nenhum vetor órfão". A reindexação (ingestão idempotente) usa o mesmo delete-por-documento antes de reinserir.
- Filtros por metadado no retrieval usam os mesmos campos persistidos no Postgres/payload.
- Retrieval usa o mesmo modelo de embeddings (`embeddinggemma-300m`, via LM Studio) da indexação.
- A conexão com o Milvus é configurável (host/porta) para casar com o container em `ops/`.
