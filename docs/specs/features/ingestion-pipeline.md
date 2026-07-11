---
id: FEAT-INGEST-001
title: Pipeline de Ingestão
version: 0.11.1
status_spec: aprovada
status_impl: implementada
owner: -
created: 2026-07-09
updated: 2026-07-11
contracts: [upload-and-metadata]
depends_on: [FEAT-UPLOAD-001]
adrs: [ADR-0001, ADR-0002, ADR-0004, ADR-0007, ADR-0009, ADR-0010, ADR-0011, ADR-0012, ADR-0013]
---

# Feature — Pipeline de Ingestão

## 1. Visão geral
Transforma um documento submetido em chunks vetorizados e indexados no Milvus, de forma idempotente e rastreável, tornando o conteúdo pesquisável semanticamente.

## 2. Contexto e problema
Após o upload (FEAT-UPLOAD-001), o documento é só um arquivo. Para responder perguntas com RAG, é preciso extrair texto, dividir em trechos, gerar embeddings e indexá-los — mantendo cada trecho rastreável para citação.

## 3. Escopo
### Incluído
- **Worker daemon** que consome a fila `ingestion_job` no Postgres (ADR-0004).
- Extração de texto por família de formato (ADR-0002): texto/MD direto; PDF/DOCX por parser; HTML sem marcação; XLS/XLSX por aba/linha; `.py` por blocos lógicos; **PPT/PPTX** (texto por slide — título/corpo/notas — via `python-pptx`, imagens dos slides via vision best-effort); **`.ipynb`** (células markdown + código, na ordem do notebook; saídas textuais opcionais); **imagens** (`.png/.jpg/.jpeg/.gif/.bmp/.webp/.tiff`, descritas por vision; fallback = nome do arquivo). — ADR-0002 (rev. 2026-07-10).
- **Chunking adaptativo por `doc_type` (ADR-0013, ADR-0006):** `size` e `overlap` configuráveis por variável de ambiente por tipo de documento; fallback para o default global (`chunk_size_words`/`chunk_overlap_words`) quando o `doc_type` não tem configuração específica (ex.: `Outro`) ou é `None`. Chunk < 2048 tokens do modelo.
- **Log detalhado de ingestão (ADR-0011):** ao concluir, o worker registra o resumo do processamento no console e no evento `job_indexed` do `system_log` — no **`message`** (resumo legível, exibido na tela Logs & Saúde) e no **`context`** (mesmos campos estruturados, para consulta/tuning): `doc_type` + perfil aplicado (específico/fallback), tamanho do texto extraído, `chunk_size`/`overlap`, contagem de chunks e tokens por chunk (min/avg/max), nº de vetores, `vision_enabled` e `duration_ms`.
- Geração de embeddings **em lote** com `embeddinggemma-300m` (768, COSINE) via LM Studio (`/v1/embeddings`).
- **Classificação por IA (ADR-0007):** sugere `title` (quando vazio no upload), `category`/`subcategory` dentro da **taxonomia fixa** ([reference/taxonomy.md](../reference/taxonomy.md)) e gera `summary`, gravados no `document` com `classification_source = llm` (editável depois pelo usuário via `PATCH /documents/{id}`). **Best-effort** (falha não interrompe a ingestão); falha registra evento `llm_classification_failed` no `system_log` (ADR-0011), além do log de console.
- Indexação no Milvus (payload inclui `squad_id`/`delivery_process_id`/`category`/`subcategory`) e persistência dos chunks no Postgres.
- Preenche `ingested_at` ao concluir; gestão de estado do `ingestion_job` e reprocessamento idempotente.
- **Descrição de imagens por LLM vision (ADR-0012):** quando `VISION_ENABLED` (default `true`), imagens embutidas em **PDF e DOCX** são extraídas, descritas por um modelo vision via LM Studio (`VISION_MODEL`) e **intercaladas no texto** — formato `[Imagem — página N: …]` / `[Imagem — parágrafo N: …]` — antes do chunking. **Best-effort** (falha não interrompe a ingestão); sem mudança no contrato do índice nem no schema. Falha registra evento `llm_vision_failed` no `system_log` (ADR-0011), além do log de console.
### Fora de escopo
- Retrieval e geração de resposta (ver FEAT-QUERY-001).
- OCR (Tesseract) — fora da POC.

## 4. Atores e pré-condições
- **Ator:** job de ingestão disparado pela API após upload.
- **Pré-condições:** `document` criado; contrato do índice definido (modelo/dimensão/métrica em `architecture/vector-index.md`).

Processamento **assíncrono** por um **worker daemon** separado da API (ADR-0004). O upload apenas cria o `ingestion_job` como `pending` e responde na hora.

### Fluxo principal
1. (Worker) Reivindica um job elegível (`pending` com `available_at<=now()` **ou** `processing` com heartbeat velho) via `SELECT ... FOR UPDATE SKIP LOCKED`, marca `processing`, incrementa `attempts` e inicia heartbeat (ADR-0009). Permite N workers em paralelo.
2. (Worker) Extrai texto conforme o tipo do arquivo.
3. (Worker) Faz chunking (tamanho/overlap), registrando posição e origem de cada chunk.
4. (Worker → LM Studio) Gera embeddings dos chunks **em lote** com `embeddinggemma-300m` (768).
5. (Worker → Milvus) Indexa vetores com `chunk_id` e payload (`squad_id`/`delivery_process_id`/`category`/`subcategory`/`doc_type`/`tags`); (→ Postgres) persiste os chunks.
6. (Worker → LM Studio) **Classifica**: sugere `title` (se vazio), `category`/`subcategory` (dentro da taxonomia) e gera `summary`; grava no `document` (`classification_source = llm`). Conteúdo tratado como entrada não confiável.
7. (Worker) Preenche `ingested_at` e marca `ingestion_job` como `indexed`.
### Fluxos alternativos e de erro
- Reprocessamento do mesmo documento → não duplica chunks nem vetores (idempotência por documento).
- **Falha transitória** (LM Studio/Milvus indisponível, timeout) → volta a `pending` com backoff (`available_at`); até `WORKER_MAX_ATTEMPTS` tentativas (ADR-0009).
- **Falha permanente** (extração impossível, arquivo corrompido) → `failed` imediato, sem retry.
- Tentativas esgotadas → `failed` terminal com `error` e `attempts`.
- Worker interrompido no meio → job preso em `processing` com heartbeat velho é recuperado pela query de claim após `WORKER_VISIBILITY_TIMEOUT` (ADR-0009); reprocessar é seguro (idempotência).

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
- `document`: escreve `title` (se sugerido)/`category_id`/`subcategory_id`/`summary`/`classification_source`/`ingested_at` na classificação (ADR-0007).
- `ingestion_job`: estados `pending`/`processing`/`indexed`/`failed`, `error`, timestamps + `attempts`/`started_at`/`heartbeat_at`/`available_at` (fila/retry — ADR-0009).
- Milvus: `vector` + `chunk_id` + payload de metadados filtráveis (inclui `squad_id`/`delivery_process_id`/`category`/`subcategory`).

## 9. Segurança, privacidade e riscos
- Conteúdo é entrada não confiável; sanitizar antes de usar em prompts (mitiga prompt injection na etapa de query **e na classificação por IA**).
- Classificação/resumo por IA a partir do conteúdo → prompt injection pode envenenar `category`/`subcategory`/`summary`; restringir a saída à taxonomia e permitir override do usuário (`classification_source`).
- **Prompt injection via imagem (ADR-0012):** o conteúdo visual é entrada não confiável e pode conter instruções embutidas; o system prompt do serviço vision instrui o modelo a ignorá-las e o conteúdo bruto da imagem não é logado. A descrição resultante é tratada como texto do documento (mesmo regime de confiança dos demais chunks).
- Risco de custo/latência na geração de embeddings em lote → considerar batching.
- PII presente nos chunks herda o tratamento sensível do documento.

## 10. Critérios de aceite
- [ ] Reprocessar um documento não duplica chunks nem vetores.
- [ ] Cada chunk indexado é rastreável até o documento e ao vetor.
- [ ] Falha de ingestão marca `failed` com erro registrado.

## 11. Testes esperados
- **Unitário:** chunking (tamanho/overlap/posição); extração por tipo; classificação transitório vs permanente do erro; cálculo do backoff.
- **Integração:** indexação Milvus + persistência Postgres em conjunto; claim recupera job com heartbeat velho; retry respeita `available_at` e `max_attempts`.
- **Fluxo:** documento → `indexed`; reprocesso idempotente; worker morto no meio → job recuperado e concluído.
- **Avaliação (RAG):** N/A direta (habilita a avaliação de FEAT-QUERY-001).
- **Regressão:** contrato do índice (modelo/dimensão/métrica) e estratégia de chunking; concorrência de N workers sem duplicar (SKIP LOCKED).

## 12. Dependências
- FEAT-UPLOAD-001 (documento criado).
- `architecture/vector-index.md` (contrato do índice fixado: embeddinggemma-300m/768/COSINE).
- Parsers por formato; `pymilvus`; cliente OpenAI-compatível (LM Studio); LM Studio com o modelo de embedding carregado.

## 13. Decisões relacionadas (ADRs)
- ADR-0001 — stack. ADR-0002 — embeddings locais, formatos e runtime do Milvus. ADR-0004 — worker daemon assíncrono. ADR-0007 — organização Squad/Processo e classificação. ADR-0009 — retry, visibility timeout e recuperação de jobs presos. ADR-0010 — exclusão remove chunks + vetores (mesmo mecanismo idempotente `delete_by_document`). ADR-0011 — worker emite eventos no `system_log` (`worker_started`/`worker_heartbeat`/`job_indexed`/`job_retry`/`job_failed`). ADR-0012 — descrição de imagens por LLM vision (best-effort) intercalada no texto antes do chunking; PyMuPDF (AGPL) para extrair imagens do PDF. ADR-0013 — chunking adaptativo por `doc_type` (perfis `size`/`overlap` por tipo, todos por env; fallback global) e `doc_type` obrigatório no upload.

## 14. Pendências e questões em aberto
- Calibrar valores de `chunk_size`/`overlap` por `doc_type` com avaliação de retrieval (golden set de perguntas + recall/precisão) — os defaults são estimativas razoáveis, não valores medidos (ADR-0013).
- Listas de taxonomia definidas em [reference/taxonomy.md](../reference/taxonomy.md); resta definir o **prompt de classificação/resumo** que restringe a saída a essa taxonomia (ADR-0007).

## 15. Histórico de atualizações
| Data | Versão | Autor | Mudança | Ref (workflow/ADR) |
|---|---|---|---|---|
| 2026-07-11 | 0.11.1 | - | Falhas best-effort de LLM (classificação e vision) passam a registrar evento (`llm_classification_failed`/`llm_vision_failed`) no `system_log`/tela Logs & Saúde, não só no console | WORK-008, ADR-0011 |
| 2026-07-10 | 0.11.0 | - | Extração para novos formatos: PPT/PPTX (slides+notas, imagens via vision), `.ipynb` (markdown+código) e imagens (via vision) | WORK-007, ADR-0002 (rev.) |
| 2026-07-10 | 0.10.0 | - | Chunking adaptativo por doc_type: perfis size/overlap por tipo, todos configuráveis via env (fallback global) | WORK-006, ADR-0013 |
| 2026-07-10 | 0.9.0 | - | Descrição de imagens por LLM vision (best-effort) intercalada no texto antes do chunking, em PDF e DOCX; habilitável por `VISION_ENABLED`; PyMuPDF para extrair imagens do PDF | WORK-005, ADR-0012 |
| 2026-07-09 | 0.8.0 | - | Exclusão de documento remove chunks + vetores (`delete_by_document`); worker emite eventos no `system_log` (start/heartbeat/indexed/retry/failed) | WORK-003, ADR-0010, ADR-0011 |
| 2026-07-09 | 0.7.0 | - | Política de retry/backoff, visibility timeout e recuperação de jobs presos; campos `attempts`/`started_at`/`heartbeat_at`/`available_at` | ADR-0009 |
| 2026-07-09 | 0.6.0 | - | IA também sugere `title` (quando vazio no upload) | ADR-0007 |
| 2026-07-09 | 0.5.0 | - | Passo de classificação por IA: sugere categoria/subcategoria (taxonomia) + resumo, editável pelo usuário; payload Milvus com squad/processo/categoria; `ingested_at` | ADR-0007 |
| 2026-07-09 | 0.4.0 | - | Ingestão passa a ser assíncrona via worker daemon + fila Postgres; embeddings em lote | ADR-0004 |
| 2026-07-09 | 0.3.0 | - | Embeddings migrados para `embeddinggemma-300m` (768) via LM Studio | ADR-0002 (rev.) |
| 2026-07-09 | 0.2.0 | - | Embeddings (bge-m3), extração por formato e chunking default fixados; spec aprovada | ADR-0002 |
| 2026-07-09 | 0.1.0 | - | Criação inicial da spec | ADR-0001 |
