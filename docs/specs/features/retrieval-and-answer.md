---
id: FEAT-QUERY-001
title: Consulta e Resposta com Citações
version: 0.5.0
status_spec: aprovada
status_impl: implementada
owner: -
created: 2026-07-09
updated: 2026-07-09
contracts: [query-and-citations]
depends_on: [FEAT-INGEST-001]
adrs: [ADR-0001, ADR-0002, ADR-0007, ADR-0008, ADR-0011]
---

# Feature — Consulta e Resposta com Citações

## 1. Visão geral
Responde perguntas em linguagem natural com base nos documentos indexados, sempre citando a origem. É o valor final da POC de RAG.

## 2. Contexto e problema
Com documentos ingeridos e indexados, o usuário precisa perguntar e receber respostas confiáveis e verificáveis. Sem grounding, a resposta perde utilidade; por isso a citação é obrigatória.

## 3. Escopo
### Incluído
- Consulta em linguagem natural com filtros opcionais por metadado (inclui `squad`/`delivery_process`, ADR-0007).
- Retrieval top-k no Milvus e montagem de contexto.
- **Expansão por vínculos (ADR-0008):** 1 salto seguindo `document_link` — inclui alvos de `esclarece`/`complementa`/`precede`; exclui alvos de `substitui` (obsoletos).
- Geração de resposta com citações (documento/trecho) e **`linked_flow[]`** informando o fluxo de documentos vinculados considerados.
- Sinalização de "sem contexto suficiente".
- **Auditoria da consulta (ADR-0011):** toda `/query` é gravada no `query_log` com métricas (scores, modelos, params de chunking, latência); a resposta traz `query_id`.
- **Feedback 👍/👎** da resposta (`POST /query/{query_id}/feedback`) para avaliar qualidade e azeitar modelo/chunk.
### Fora de escopo
- Conversa multi-turno com memória (fora da POC).
- Expansão multi-salto (transitiva) de vínculos — só 1 salto na POC (ADR-0008).
- Reranking avançado (pode virar melhoria posterior via ADR).

## 4. Atores e pré-condições
- **Ator:** usuário da UI Django.
- **Pré-condições:** ao menos um documento em estado `indexed`; contrato do índice ativo.

## 5. Comportamento e fluxos
### Fluxo principal
1. (Django) Usuário envia uma pergunta (com filtros opcionais).
2. (FastAPI → LM Studio) Gera embedding da pergunta com `embeddinggemma-300m` (mesmo modelo do índice).
3. (FastAPI → Milvus) Busca top-k (default 5) por similaridade COSINE, aplicando filtros por metadado.
4. (FastAPI → Postgres) Recupera os chunks correspondentes; **expande 1 salto** pelos `document_link` dos documentos recuperados (inclui `esclarece`/`complementa`/`precede`; exclui `substitui`) e monta o contexto (deduplicando, respeitando limite).
5. (FastAPI → LM Studio) Gera a resposta (API OpenAI-compatível) e anexa `citations[]` (documento, chunk, trecho, score) e `linked_flow[]` (vínculos considerados/excluídos).
6. (Django) Exibe resposta, citações e o fluxo de documentos relacionados.
### Fluxos alternativos e de erro
- Nenhum chunk relevante / abaixo de limiar → resposta indica ausência de contexto (não alucina).
- Filtro sem resultados → sinaliza que não há documentos no recorte.
- Documento recuperado com alvo `substitui` → alvo obsoleto excluído do contexto e sinalizado no `linked_flow[]`.
- Falha do modelo/índice → erro claro, sem resposta fabricada.

## 6. Regras de domínio
- Toda resposta cita chunks reais recuperados (grounding obrigatório).
- Sem contexto suficiente, sinalizar em vez de inventar.
- Consulta usa o mesmo modelo de embeddings da indexação (`embeddinggemma-300m`).
- Expansão por vínculos é de **1 salto** e respeita o tipo: `substitui` nunca entra no contexto (conteúdo obsoleto). O grafo de vínculos vive no Postgres; Milvus não muda (ADR-0008).
- Conteúdo dos chunks (inclusive dos documentos expandidos) é entrada não confiável ao montar o prompt (mitigar prompt injection).

## 7. Contratos e integrações
- Contrato: `query-and-citations` (`POST /query` → resposta com `query_id`, `citations[]`, `linked_flow[]`; `POST /query/{query_id}/feedback`).
- Integrações: Milvus (busca vetorial) e Postgres (chunks/metadados, grafo `document_link`, `query_log`).

## 8. Dados e persistência
- Leitura de `chunk`, metadados e `document_link` (expansão de contexto).
- `query_log` (ADR-0011): **toda** consulta gravada — pergunta, filtros, `top_k`, resposta, citações, `linked_flow`, `scores[]`, ids recuperados, `embedding_model`/`chat_model`, params de chunking, `retrieval_min_score`, `latency_ms`, e `rating`/`rating_at` (feedback). Sem FK para `document`/`chunk` (snapshot — sobrevive à exclusão).

## 9. Segurança, privacidade e riscos
- Prompt injection via conteúdo dos documentos → isolar/sanitizar contexto.
- Vazamento de PII em respostas → citações permitem rastrear e auditar a origem.
- Risco de alucinação → mitigado por grounding e limiar de similaridade.

## 10. Critérios de aceite
- [x] Resposta cita chunks reais recuperados (grounding).
- [x] Sem contexto suficiente, a API sinaliza em vez de alucinar.
- [x] Filtros por metadado restringem corretamente o retrieval.
- [x] Toda consulta grava `query_log` com métricas; a resposta traz `query_id`.
- [x] Feedback 👍/👎 grava `rating`/`rating_at`; `query_id` inexistente → `404`; rating inválido → `422`.

## 11. Testes esperados
- **Unitário:** montagem de contexto/prompt; deduplicação; limiar.
- **Integração:** retrieval Milvus + geração ponta a ponta.
- **Fluxo:** pergunta → resposta com citações exibida na UI.
- **Avaliação (RAG):** recall/precisão em conjunto fixo de perguntas; checagem de grounding.
- **Regressão:** contrato `query-and-citations`; consistência com o modelo de embeddings; expansão por vínculos (1 salto; `substitui` sempre excluído do contexto).

## 12. Dependências
- FEAT-INGEST-001 (documentos indexados).
- Contrato do índice fixado em `architecture/vector-index.md`.
- LM Studio ativo (API OpenAI-compatível) para embedding da pergunta e geração — modelos de embedding e chat carregados.

## 13. Decisões relacionadas (ADRs)
- ADR-0001 — stack. ADR-0002 — embeddings locais e LLM via LM Studio. ADR-0007 — filtros por squad/processo. ADR-0008 — expansão de retrieval por vínculos + `linked_flow[]`. ADR-0011 — `query_log` (auditoria + métricas) e feedback 👍/👎.

## 14. Pendências e questões em aberto
- Calibrar limiar de similaridade COSINE para "sem contexto suficiente" (`top_k` default 5 já fixado). O `query_log` (scores/rating/latency) agora fornece dados para essa calibração.
- ~~Definir se `query_log` entra na POC~~ → **resolvido (ADR-0011): entra, gravando toda consulta.**

## 15. Histórico de atualizações
| Data | Versão | Autor | Mudança | Ref (workflow/ADR) |
|---|---|---|---|---|
| 2026-07-09 | 0.5.0 | - | `query_log` (toda consulta + métricas de tuning) e feedback 👍/👎; `query_id` na resposta | WORK-003, ADR-0011 |
| 2026-07-09 | 0.4.0 | - | Filtros por squad/processo; expansão de retrieval por vínculos (1 salto, `substitui` excluído) + `linked_flow[]` na resposta | ADR-0007, ADR-0008 |
| 2026-07-09 | 0.3.0 | - | Embedding da pergunta via `embeddinggemma-300m` (LM Studio) | ADR-0002 (rev.) |
| 2026-07-09 | 0.2.0 | - | Geração via LM Studio, embeddings bge-m3 e top_k default fixados; spec aprovada | ADR-0002 |
| 2026-07-09 | 0.1.0 | - | Criação inicial da spec | ADR-0001 |
