---
id: FEAT-INGEST-001
title: Pipeline de Ingestão
version: 0.4.0
status_spec: aprovada
status_impl: nao_iniciada
owner: -
created: 2026-07-09
updated: 2026-07-09
contracts: [upload-and-metadata]
depends_on: [FEAT-UPLOAD-001]
adrs: [ADR-0001, ADR-0002, ADR-0004]
---

# Feature — Pipeline de Ingestão

## 1. Visão geral
Transforma um documento submetido em chunks vetorizados e indexados no Milvus, de forma idempotente e rastreável, tornando o conteúdo pesquisável semanticamente.

## 2. Contexto e problema
Após o upload (FEAT-UPLOAD-001), o documento é só um arquivo. Para responder perguntas com RAG, é preciso extrair texto, dividir em trechos, gerar embeddings e indexá-los — mantendo cada trecho rastreável para citação.

## 3. Escopo
### Incluído
- **Worker daemon** que consome a fila `ingestion_job` no Postgres (ADR-0004).
- Extração de texto por família de formato (ADR-0002): texto/MD direto; PDF/DOCX por parser; HTML sem marcação; XLS/XLSX por aba/linha; `.py` por blocos lógicos.
- Chunking com tamanho/overlap definidos (default: ~512 tokens, overlap ~64 — ajustável; chunk < 2048 tokens do modelo).
- Geração de embeddings **em lote** com `embeddinggemma-300m` (768, COSINE) via LM Studio (`/v1/embeddings`).
- Indexação no Milvus e persistência dos chunks no Postgres.
- Gestão de estado do `ingestion_job` e reprocessamento idempotente.
### Fora de escopo
- Retrieval e geração de resposta (ver FEAT-QUERY-001).
- OCR de imagens/scan (fora da POC, salvo decisão em ADR).

## 4. Atores e pré-condições
- **Ator:** job de ingestão disparado pela API após upload.
- **Pré-condições:** `document` criado; contrato do índice definido (modelo/dimensão/métrica em `architecture/vector-index.md`).

Processamento **assíncrono** por um **worker daemon** separado da API (ADR-0004). O upload apenas cria o `ingestion_job` como `pending` e responde na hora.

### Fluxo principal
1. (Worker) Reivindica um job `pending` com `SELECT ... FOR UPDATE SKIP LOCKED` e marca `processing` (permite N workers em paralelo).
2. (Worker) Extrai texto conforme o tipo do arquivo.
3. (Worker) Faz chunking (tamanho/overlap), registrando posição e origem de cada chunk.
4. (Worker → LM Studio) Gera embeddings dos chunks **em lote** com `embeddinggemma-300m` (768).
5. (Worker → Milvus) Indexa vetores com `chunk_id`; (→ Postgres) persiste os chunks.
6. (Worker) Marca `ingestion_job` como `indexed`.
### Fluxos alternativos e de erro
- Reprocessamento do mesmo documento → não duplica chunks nem vetores (idempotência por documento).
- Falha em qualquer etapa → estado `failed` com erro registrado; nada fica parcialmente indexado de forma órfã.
- Worker interrompido no meio → job volta a ficar disponível para reivindicação (sem perder o pending).

## 6. Regras de domínio
- Ingestão é idempotente: reprocessar substitui de forma consistente, sem duplicatas.
- Todo chunk indexado é rastreável até o `document` e ao vetor no Milvus (base para citações).
- Modelo/dimensão/métrica de embeddings são contrato do índice: mudança exige ADR + reindexação.
- Chunking (tamanho/overlap/critério) é decisão de qualidade e deve ser documentado.

## 7. Contratos e integrações
- Estado exposto via `GET /documents/{id}` do contrato `upload-and-metadata`.
- Integrações: Milvus (coleção de vetores) e Postgres (`chunk`, `ingestion_job`).

## 8. Dados e persistência
- `chunk`: texto, posição/ordem, FK para `document`, id do vetor no Milvus.
- `ingestion_job`: estados `pending`/`processing`/`indexed`/`failed`, erro, timestamps.
- Milvus: `vector` + `chunk_id` + payload de metadados filtráveis.

## 9. Segurança, privacidade e riscos
- Conteúdo é entrada não confiável; sanitizar antes de usar em prompts (mitiga prompt injection na etapa de query).
- Risco de custo/latência na geração de embeddings em lote → considerar batching.
- PII presente nos chunks herda o tratamento sensível do documento.

## 10. Critérios de aceite
- [ ] Reprocessar um documento não duplica chunks nem vetores.
- [ ] Cada chunk indexado é rastreável até o documento e ao vetor.
- [ ] Falha de ingestão marca `failed` com erro registrado.

## 11. Testes esperados
- **Unitário:** chunking (tamanho/overlap/posição); extração por tipo.
- **Integração:** indexação Milvus + persistência Postgres em conjunto.
- **Fluxo:** documento → `indexed`; reprocesso idempotente.
- **Avaliação (RAG):** N/A direta (habilita a avaliação de FEAT-QUERY-001).
- **Regressão:** contrato do índice (modelo/dimensão/métrica) e estratégia de chunking.

## 12. Dependências
- FEAT-UPLOAD-001 (documento criado).
- `architecture/vector-index.md` (contrato do índice fixado: embeddinggemma-300m/768/COSINE).
- Parsers por formato; `pymilvus`; cliente OpenAI-compatível (LM Studio); LM Studio com o modelo de embedding carregado.

## 13. Decisões relacionadas (ADRs)
- ADR-0001 — stack. ADR-0002 — embeddings locais, formatos e runtime do Milvus. ADR-0004 — worker daemon assíncrono.

## 14. Pendências e questões em aberto
- Calibrar tamanho/overlap de chunking por família de formato (default definido; ajuste após avaliação de retrieval).

## 15. Histórico de atualizações
| Data | Versão | Autor | Mudança | Ref (workflow/ADR) |
|---|---|---|---|---|
| 2026-07-09 | 0.4.0 | - | Ingestão passa a ser assíncrona via worker daemon + fila Postgres; embeddings em lote | ADR-0004 |
| 2026-07-09 | 0.3.0 | - | Embeddings migrados para `embeddinggemma-300m` (768) via LM Studio | ADR-0002 (rev.) |
| 2026-07-09 | 0.2.0 | - | Embeddings (bge-m3), extração por formato e chunking default fixados; spec aprovada | ADR-0002 |
| 2026-07-09 | 0.1.0 | - | Criação inicial da spec | ADR-0001 |
