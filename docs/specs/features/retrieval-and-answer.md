---
id: FEAT-QUERY-001
title: Consulta e Resposta com Citações
version: 0.8.0
status_spec: aprovada
status_impl: implementada
owner: -
created: 2026-07-09
updated: 2026-07-11
contracts: [query-and-citations]
depends_on: [FEAT-INGEST-001]
adrs: [ADR-0001, ADR-0002, ADR-0005, ADR-0007, ADR-0008, ADR-0011, ADR-0014, ADR-0015]
---

# Feature — Consulta e Resposta com Citações

## 1. Visão geral
Responde perguntas em linguagem natural com base nos documentos indexados, sempre citando a origem. É o valor final da POC de RAG.

## 2. Contexto e problema
Com documentos ingeridos e indexados, o usuário precisa perguntar e receber respostas confiáveis e verificáveis. Sem grounding, a resposta perde utilidade; por isso a citação é obrigatória.

## 3. Escopo
### Incluído
- Consulta em linguagem natural com filtros opcionais por metadado: `squad`/`delivery_process`/`category`/`doc_type` (ADR-0007) e, a partir do WORK-010, também `delivery_phase` e `tags` (ADR-0015). `tags` aceita 1+ valores com semântica **OR** (documento com qualquer uma das tags pedidas); `delivery_phase` é igualdade simples contra a lista fechada (`reference/taxonomy.md`).
- Retrieval top-k no Milvus e montagem de contexto.
- **Expansão por vínculos (ADR-0008):** 1 salto seguindo `document_link` — inclui alvos de `esclarece`/`complementa`/`precede`; exclui alvos de `substitui` (obsoletos).
- Geração de resposta com citações (documento/trecho) e **`linked_flow[]`** informando o fluxo de documentos vinculados considerados.
- **Rebaixamento por vigência (ADR-0014):** documentos com `valid_until` no passado têm o score multiplicado por `retrieval_expired_score_factor` (default 0.5, por env) e os hits são reordenados pelo score ajustado — vencidos nunca são citados com a mesma relevância dos vigentes (rebaixados, não excluídos). Vale para `/query` e `/retrieve`.
- Sinalização de "sem contexto suficiente".
- **Auditoria da consulta (ADR-0011):** toda `/query` é gravada no `query_log` com métricas (scores, modelos, params de chunking, latência); a resposta traz `query_id`.
- **Feedback 👍/👎** da resposta (`POST /query/{query_id}/feedback`) para avaliar qualidade e azeitar modelo/chunk.
- **Retrieval puro (`POST /retrieve`, ADR-0005):** endpoint dedicado que devolve só os trechos relevantes + score, **sem geração**, sem expansão por vínculos e sem gravar `query_log`. Reusa o mesmo retrieval de `/query`; consumido pela tool `retrieve_chunks` do MCP (FEAT-MCP-001).
### Fora de escopo
- Conversa multi-turno com memória (fora da POC).
- Expansão multi-salto (transitiva) de vínculos — só 1 salto na POC (ADR-0008).
- Reranking avançado (pode virar melhoria posterior via ADR).
- Filtro de `tags` com semântica **AND** (documento precisa ter todas as tags pedidas) — só **OR** na POC (ADR-0015).

## 4. Atores e pré-condições
- **Ator:** usuário da UI Django.
- **Pré-condições:** ao menos um documento em estado `indexed`; contrato do índice ativo.

## 5. Comportamento e fluxos
### Fluxo principal
1. (Django) Usuário envia uma pergunta (com filtros opcionais).
2. (FastAPI → LM Studio) Gera embedding da pergunta com `embeddinggemma-300m` (mesmo modelo do índice).
3. (FastAPI → Milvus) Busca top-k (default 5) por similaridade COSINE, aplicando filtros por metadado — igualdade simples para `squad`/`delivery_process`/`category`/`doc_type`/`delivery_phase`; expressão `OR` de substring para `tags` (ADR-0015).
4. (FastAPI → Postgres) Recupera os chunks correspondentes; **rebaixa hits de documentos vencidos** (`valid_until < hoje` → score × `retrieval_expired_score_factor`) e reordena pelo score ajustado (ADR-0014); **expande 1 salto** pelos `document_link` dos documentos recuperados (inclui `esclarece`/`complementa`/`precede`; exclui `substitui`) e monta o contexto (deduplicando, respeitando limite).
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
- Filtros por metadado (ADR-0015): `delivery_phase` filtra por igualdade (lista fechada); `tags` filtra por **OR** — hit incluído se tiver qualquer uma das tags pedidas (payload Milvus guarda `delivery_phase`/`tags` como campo dinâmico — sem drop/recriação da coleção; tags como string delimitada por vírgula, filtro via `LIKE` por tag). Documentos ingeridos antes do WORK-010 não têm esses 2 campos populados no payload até serem reprocessados — reenfileirar o acervo é **recomendado, não bloqueante**: a busca já funciona para documentos novos/reprocessados assim que a mudança é liberada.
- Vigência (ADR-0014): documento é **vencido** quando `valid_until IS NOT NULL AND valid_until < hoje` (data, UTC). Vencidos são **rebaixados** (score ajustado), não excluídos — preserva grounding quando só há material vencido. O `query_log.scores` grava o score ajustado (o efetivamente usado). Sem mudança no índice Milvus.
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
- [x] UI de Consulta filtra por `delivery_process` (WORK-010, Fase 1) — `<select>` no form; validado por smoke test manual (sem suíte automatizada de UI nesta POC).
- [x] `/query`/`/retrieve` filtram por `delivery_phase` (igualdade) e `tags` (OR) (WORK-010, Fase 2, ADR-0015) — validado por `test_vectorstore_dynamic_fields.py` (Milvus real) + `test_retrieval_filters.py` (`_map_filters`↔`_build_filter_expr`). Só alcança documentos já reprocessados — reindexação do acervo é manual/recomendada (ver Lacunas conhecidas em `status.md`), não coberta por teste automatizado end-to-end (depende de LM Studio + worker).

## 11. Testes esperados
- **Unitário:** montagem de contexto/prompt; deduplicação; limiar; `_map_filters`/`_FILTER_MAP` (ADR-0015) — `delivery_phase` vira `k: v` direto, `tags` (lista) vira expressão `OR` de `LIKE`; escaping de `"`/`\`/`,`/`%` no valor da tag antes de montar a expressão.
- **Integração:** retrieval Milvus + geração ponta a ponta; `POST /query`/`POST /retrieve` filtrando por `delivery_phase` e por `tags` (1 tag e 2+ tags) contra um Milvus real com dados de teste.
- **Fluxo:** pergunta → resposta com citações exibida na UI; UI de Consulta com `delivery_process` selecionado restringindo o resultado.
- **Avaliação (RAG):** recall/precisão em conjunto fixo de perguntas; checagem de grounding; caso específico — documento com a tag do filtro aparece, documento sem nenhuma tag do filtro não aparece (semântica OR: documento com só 1 das N tags pedidas ainda aparece).
- **Regressão:** contrato `query-and-citations`; consistência com o modelo de embeddings; expansão por vínculos (1 salto; `substitui` sempre excluído do contexto); filtros pré-existentes (`squad`/`category`/`doc_type`) continuam funcionando isolados e combinados com os novos; rebaixamento por vigência (ADR-0014) continua aplicando mesmo com filtro de `tags`/`delivery_phase` ativo.
- **Spike técnico (ADR-0015, pré-requisito da Fase 2):** `upsert` de um chunk de teste com `delivery_phase`/`tags` como campo dinâmico + `search` com `filter` de igualdade e de `LIKE` sobre esses campos, confirmando que o Milvus 2.5.4/pymilvus 2.5.4 filtra corretamente. Só depois disso generalizar `vectorstore.py`/`retriever.py`. Se falhar: plano B do ADR (schema declarado + drop/recriação) — reabre este bloco de testes com o novo mecanismo.
- **Cenário de payload parcial (WORK-010):** documento indexado **antes** da mudança (sem `delivery_phase`/`tags` no payload) não aparece em busca filtrada por esses campos, mas continua aparecendo em busca sem filtro ou filtrada só por `squad`/`category`/`doc_type` — a ausência do campo dinâmico não pode quebrar a busca geral.

## 12. Dependências
- FEAT-INGEST-001 (documentos indexados).
- Contrato do índice fixado em `architecture/vector-index.md`.
- LM Studio ativo (API OpenAI-compatível) para embedding da pergunta e geração — modelos de embedding e chat carregados.

## 13. Decisões relacionadas (ADRs)
- ADR-0001 — stack. ADR-0002 — embeddings locais e LLM via LM Studio. ADR-0007 — filtros por squad/processo. ADR-0008 — expansão de retrieval por vínculos + `linked_flow[]`. ADR-0011 — `query_log` (auditoria + métricas) e feedback 👍/👎. ADR-0014 — rebaixamento de documentos vencidos (`valid_until`) no retrieval. ADR-0015 — filtros por `delivery_phase`/`tags` no Milvus via campo dinâmico, sem drop/recriação (revisa parcialmente o ADR-0014 quanto a `delivery_phase`).

## 14. Pendências e questões em aberto
- Calibrar limiar de similaridade COSINE para "sem contexto suficiente" (`top_k` default 5 já fixado). O `query_log` (scores/rating/latency) agora fornece dados para essa calibração.
- ~~Definir se `query_log` entra na POC~~ → **resolvido (ADR-0011): entra, gravando toda consulta.**
- ~~ADR-0015 em `proposta`~~ → **resolvido: `aceita`** — `software-architect`/`architecture-guard` validaram a fronteira e revisaram o mecanismo (campo dinâmico em vez de drop/recriação). Falta só um spike técnico de implementação (não bloqueia a decisão) confirmando `LIKE` sobre campo dinâmico nesta versão do Milvus (2.5.4) — plano B documentado no ADR se o spike falhar.
- Semântica **AND** para `tags` (documento com todas as tags pedidas) fica fora de escopo do WORK-010 — avaliar demanda antes de implementar (ADR-0015).

## 15. Histórico de atualizações
| Data | Versão | Autor | Mudança | Ref (workflow/ADR) |
|---|---|---|---|---|
| 2026-07-11 | 0.8.0 | - | Filtros de retrieval por `delivery_process` (fecha lacuna: UI ganha o `<select>`, backend já suportava) e, via ADR-0015, `delivery_phase`/`tags` no Milvus (campo dinâmico, sem drop/recriação da coleção; reindexação do acervo é recomendada, não bloqueante). Implementado e testado: pytest 68 (apps/api) | WORK-010, ADR-0015 |
| 2026-07-10 | 0.7.0 | - | Rebaixamento de documentos vencidos (`valid_until`) no retrieval — score × `retrieval_expired_score_factor`, reordenação; vale p/ `/query` e `/retrieve` | WORK-007, ADR-0014 |
| 2026-07-09 | 0.6.0 | - | Endpoint `POST /retrieve` (retrieval puro, sem geração) para o MCP; reusa o retrieval de `/query` sem gravar `query_log` | WORK-004, ADR-0005 |
| 2026-07-09 | 0.5.0 | - | `query_log` (toda consulta + métricas de tuning) e feedback 👍/👎; `query_id` na resposta | WORK-003, ADR-0011 |
| 2026-07-09 | 0.4.0 | - | Filtros por squad/processo; expansão de retrieval por vínculos (1 salto, `substitui` excluído) + `linked_flow[]` na resposta | ADR-0007, ADR-0008 |
| 2026-07-09 | 0.3.0 | - | Embedding da pergunta via `embeddinggemma-300m` (LM Studio) | ADR-0002 (rev.) |
| 2026-07-09 | 0.2.0 | - | Geração via LM Studio, embeddings bge-m3 e top_k default fixados; spec aprovada | ADR-0002 |
| 2026-07-09 | 0.1.0 | - | Criação inicial da spec | ADR-0001 |
