# Visão funcional — Milvus RAG (POC)

## Objetivo

POC que permite submeter documentos, defini-los com metadados, indexá-los semanticamente e responder perguntas em linguagem natural com base no conteúdo submetido, sempre com citações da origem.

## Jornada principal

1. Usuário faz **upload** de um ou mais documentos pela UI Django e define **metadados** (ex.: título, autor, tags, tipo).
2. Um **worker assíncrono** ingere o documento: extrai texto, faz **chunking** e gera **embeddings** (a ingestão pode ser demorada; ver ADR-0004).
3. Os embeddings são **indexados no Milvus**; metadados e chunks ficam no PostgreSQL.
4. **Consulta** por dois canais — a UI Django **e** um **servidor MCP** para outros agentes (ADR-0005): o sistema recupera os chunks relevantes e **gera uma resposta com citações**.
5. Qualidade de retrieval e grounding das respostas são **avaliáveis**.

## Escopo da POC

Incluído: upload + metadados (PDF, DOCX, TXT/MD, HTML, `.py`, XLS/XLSX), ingestão assíncrona (worker), indexação Milvus, consulta com citações por **UI Django e MCP**, avaliação básica de retrieval.

Fora do escopo (por ora): multiusuário/tenancy avançado, permissões granulares, versionamento de documentos, produção em escala.

## Stack (ADR-0001, ADR-0002)

- UI **Django**, domínio **FastAPI**, metadados em **PostgreSQL**, índice **Milvus**.
- **PostgreSQL + Milvus** em containers (Podman/Docker) via `compose` em `ops/`.
- Embeddings e geração no **LM Studio** (local, API OpenAI-compatível): `embeddinggemma-300m` (768, COSINE) para embeddings e um modelo de chat para geração.
- Processamento **local**: nenhum conteúdo sai do ambiente para vetorizar ou gerar respostas.

## Princípios

- Respostas sempre citam a origem (grounding).
- FastAPI é a fonte da verdade; Django é cliente.
- Conteúdo submetido é entrada não confiável.
- Modelo/dimensão/métrica de embeddings são contrato do índice (mudança = ADR + reindexação).
