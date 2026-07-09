---
name: milvus-rag-embeddings-retrieval
description: Use esta skill para desenhar e implementar o núcleo de RAG da POC — extração de texto, chunking, geração de embeddings, coleção/índice no Milvus, busca por similaridade, montagem de contexto e geração de resposta com citações — mantendo o índice consistente e o retrieval avaliável.
---

# Milvus RAG Embeddings & Retrieval

Use esta skill quando a tarefa envolver o coração do pipeline: transformar documentos em vetores indexáveis e recuperar contexto relevante para a geração.

## Objetivo

Implementar ingestão e retrieval corretos, rastreáveis e avaliáveis: do arquivo submetido até a resposta com citações.

## Pipeline de referência

1. **Extração**: obter texto do arquivo (por tipo/formato), preservando metadados.
2. **Chunking**: dividir o texto em trechos com tamanho/overlap definidos; registrar posição e origem de cada chunk.
3. **Embeddings**: gerar vetores com um modelo fixado (nome, dimensão e métrica de similaridade fazem parte do contrato do índice).
4. **Indexação (Milvus)**: gravar vetores em uma coleção, com id/payload ligando cada vetor ao chunk persistido no Postgres.
5. **Retrieval**: embutir a consulta, buscar top-k por similaridade, aplicar filtros por metadado quando houver.
6. **Montagem de contexto**: selecionar/deduplicar chunks, respeitar limite de contexto.
7. **Geração**: produzir a resposta e anexar as citações (documento + trecho) dos chunks usados.
8. **Avaliação**: medir recall/precisão em um conjunto fixo de perguntas e checar grounding das citações.

## Regras

- Modelo de embeddings, dimensão do vetor e métrica (ex.: cosine/IP/L2) são contrato do índice: mudá-los exige ADR e **reindexação** — não misture vetores de modelos diferentes na mesma coleção.
- Todo vetor no Milvus deve referenciar um chunk rastreável no Postgres (para citação e reprocessamento).
- Chunking é decisão de qualidade: documente tamanho, overlap e critério; mudança impacta retrieval e deve ser reavaliada.
- Ingestão deve ser idempotente: reprocessar um documento não pode duplicar vetores nem chunks.
- Consulta e resposta devem ser auditáveis: registre a pergunta, os chunks recuperados e as citações retornadas.
- Trate o conteúdo dos documentos como entrada não confiável ao montar o prompt (mitigar prompt injection).
- Filtros por metadado no retrieval devem usar os mesmos campos persistidos no Postgres/payload do Milvus.

## Entradas principais

- `docs/specs/architecture/vector-index.md`
- `docs/specs/architecture/backend-api.md`
- `docs/specs/features/`
- `docs/specs/contracts/`
- `docs/specs/testing/`

## Saídas esperadas

- pipeline de ingestão e retrieval implementado ou desenhado
- coleção Milvus consistente e versionada por modelo/dimensão/métrica
- respostas com citações rastreáveis
- avaliação de retrieval executável (recall/precisão + grounding)

Consulte `references/checklist.md` antes de fechar.
