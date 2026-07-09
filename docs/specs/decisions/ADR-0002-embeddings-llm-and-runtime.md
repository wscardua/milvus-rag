# ADR-0002 — Embeddings e LLM via LM Studio, formatos e runtime containerizado

## Contexto

A POC precisa fixar o contrato do índice (modelo/dimensão/métrica de embeddings), o motor de geração da resposta, os formatos de documento aceitos e o modo de execução da infraestrutura. Essas decisões destravam a especificação de ingestão e consulta e não podem ficar implícitas. Preferência por processamento **local** e por concentrar a inferência (embeddings + geração) num único servidor.

## Decisão

- **Embeddings — via LM Studio.** Modelo `embeddinggemma-300m` (Google, base Gemma 3), servido pelo LM Studio no endpoint **OpenAI-compatível** `/v1/embeddings`. Multilíngue (PT-BR incluído), **dimensão 768** (MRL disponível para 512/256/128; a POC usa 768 cheio), métrica `COSINE`, contexto 2048 tokens. O backend consome como cliente HTTP — sem `sentence-transformers` no processo.
- **Geração (LLM) — via LM Studio.** Mesmo servidor local, endpoint `/v1/chat/completions`. `base_url`, modelo e chave configuráveis por ambiente (ex.: `http://localhost:1234/v1`). O modelo de chat concreto é o carregado no LM Studio (não fixado aqui). Embeddings e chat ficam carregados simultaneamente no LM Studio.
- **Formatos aceitos no upload.** PDF, DOCX, TXT/Markdown, HTML, `.py` (código), XLS/XLSX (planilha). Extração e chunking por família:
  - texto/markdown: direto;
  - PDF/DOCX: extração de texto por parser;
  - HTML: extração do conteúdo textual (remover marcação);
  - XLS/XLSX: serialização por aba/linha em texto;
  - `.py`: chunking por blocos lógicos preservando contexto.
  - Chunk máximo deve caber no contexto do embedding (< 2048 tokens); default ~512 tokens, overlap ~64.
- **Infra containerizada — Podman/Docker.** `PostgreSQL` e `Milvus` sobem juntos via `compose` em `ops/`. Runtime alvo: **Podman** (`podman compose`), compatível com o `docker-compose.yml` padrão. Conexões (host/porta) configuráveis no backend.

## Impacto

- `docs/specs/architecture/vector-index.md` fixa `embeddinggemma-300m` / 768 / COSINE / HNSW.
- Trocar modelo de embeddings ou dimensão/métrica exige novo ADR + reindexação total.
- Backend depende de: `pymilvus`, cliente OpenAI-compatível (embeddings + chat via LM Studio) e parsers de documento. **Não** depende de `sentence-transformers`.
- Ingestão precisa de extratores por formato; XLS e `.py` têm chunking específico.
- Execução local depende do **LM Studio ativo com dois modelos carregados** (embedding + chat) e dos containers Postgres + Milvus no ar (Podman).

## Alternativas rejeitadas

- **Embeddings via `sentence-transformers` no backend (bge-m3)**: descartado — preferência por concentrar a inferência no LM Studio e deixar o backend como cliente leve. EmbeddingGemma cobre PT com modelo menor.
- **Embeddings via API na nuvem (OpenAI/Voyage/Cohere)**: descartado — processamento local, sem custo de API nem saída de dados.
- **LLM via API na nuvem (Anthropic/OpenAI/watsonx)**: descartado para a POC em favor do LM Studio local.
- **Milvus Lite (embedded)**: descartado — standalone via container aproxima de produção e isola o índice.
- **pgvector no lugar do Milvus**: fora do escopo (índice dedicado = Milvus, ver ADR-0001).

## Data

2026-07-09

## Status

aceita

> Revisão 2026-07-09: embeddings migrados de `sentence-transformers`/bge-m3 (1024) para `embeddinggemma-300m` (768) servido pelo LM Studio; Postgres adicionado ao compose containerizado (Podman). Decisão anterior nunca chegou a implementação.
