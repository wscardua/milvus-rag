---
id: FEAT-QUERY-001
title: Consulta e Resposta com Citações
version: 0.3.0
status_spec: aprovada
status_impl: nao_iniciada
owner: -
created: 2026-07-09
updated: 2026-07-09
contracts: [query-and-citations]
depends_on: [FEAT-INGEST-001]
adrs: [ADR-0001, ADR-0002]
---

# Feature — Consulta e Resposta com Citações

## 1. Visão geral
Responde perguntas em linguagem natural com base nos documentos indexados, sempre citando a origem. É o valor final da POC de RAG.

## 2. Contexto e problema
Com documentos ingeridos e indexados, o usuário precisa perguntar e receber respostas confiáveis e verificáveis. Sem grounding, a resposta perde utilidade; por isso a citação é obrigatória.

## 3. Escopo
### Incluído
- Consulta em linguagem natural com filtros opcionais por metadado.
- Retrieval top-k no Milvus e montagem de contexto.
- Geração de resposta com citações (documento/trecho).
- Sinalização de "sem contexto suficiente".
### Fora de escopo
- Conversa multi-turno com memória (fora da POC).
- Reranking avançado (pode virar melhoria posterior via ADR).

## 4. Atores e pré-condições
- **Ator:** usuário da UI Django.
- **Pré-condições:** ao menos um documento em estado `indexed`; contrato do índice ativo.

## 5. Comportamento e fluxos
### Fluxo principal
1. (Django) Usuário envia uma pergunta (com filtros opcionais).
2. (FastAPI → LM Studio) Gera embedding da pergunta com `embeddinggemma-300m` (mesmo modelo do índice).
3. (FastAPI → Milvus) Busca top-k (default 5) por similaridade COSINE, aplicando filtros por metadado.
4. (FastAPI → Postgres) Recupera os chunks correspondentes e monta o contexto (deduplicando, respeitando limite).
5. (FastAPI → LM Studio) Gera a resposta (API OpenAI-compatível) e anexa `citations[]` (documento, chunk, trecho, score).
6. (Django) Exibe resposta e citações.
### Fluxos alternativos e de erro
- Nenhum chunk relevante / abaixo de limiar → resposta indica ausência de contexto (não alucina).
- Filtro sem resultados → sinaliza que não há documentos no recorte.
- Falha do modelo/índice → erro claro, sem resposta fabricada.

## 6. Regras de domínio
- Toda resposta cita chunks reais recuperados (grounding obrigatório).
- Sem contexto suficiente, sinalizar em vez de inventar.
- Consulta usa o mesmo modelo de embeddings da indexação (`embeddinggemma-300m`).
- Conteúdo dos chunks é entrada não confiável ao montar o prompt (mitigar prompt injection).

## 7. Contratos e integrações
- Contrato: `query-and-citations` (`POST /query`).
- Integrações: Milvus (busca vetorial) e Postgres (chunks/metadados; opcional `query_log`).

## 8. Dados e persistência
- Leitura de `chunk` e metadados.
- Opcional: `query_log` (pergunta, chunks recuperados, citações) para auditoria/avaliação.

## 9. Segurança, privacidade e riscos
- Prompt injection via conteúdo dos documentos → isolar/sanitizar contexto.
- Vazamento de PII em respostas → citações permitem rastrear e auditar a origem.
- Risco de alucinação → mitigado por grounding e limiar de similaridade.

## 10. Critérios de aceite
- [ ] Resposta cita chunks reais recuperados (grounding).
- [ ] Sem contexto suficiente, a API sinaliza em vez de alucinar.
- [ ] Filtros por metadado restringem corretamente o retrieval.

## 11. Testes esperados
- **Unitário:** montagem de contexto/prompt; deduplicação; limiar.
- **Integração:** retrieval Milvus + geração ponta a ponta.
- **Fluxo:** pergunta → resposta com citações exibida na UI.
- **Avaliação (RAG):** recall/precisão em conjunto fixo de perguntas; checagem de grounding.
- **Regressão:** contrato `query-and-citations`; consistência com o modelo de embeddings.

## 12. Dependências
- FEAT-INGEST-001 (documentos indexados).
- Contrato do índice fixado em `architecture/vector-index.md`.
- LM Studio ativo (API OpenAI-compatível) para embedding da pergunta e geração — modelos de embedding e chat carregados.

## 13. Decisões relacionadas (ADRs)
- ADR-0001 — stack. ADR-0002 — embeddings locais e LLM via LM Studio.

## 14. Pendências e questões em aberto
- Calibrar limiar de similaridade COSINE para "sem contexto suficiente" (`top_k` default 5 já fixado).
- Definir se `query_log` entra na POC (auditoria/avaliação).

## 15. Histórico de atualizações
| Data | Versão | Autor | Mudança | Ref (workflow/ADR) |
|---|---|---|---|---|
| 2026-07-09 | 0.3.0 | - | Embedding da pergunta via `embeddinggemma-300m` (LM Studio) | ADR-0002 (rev.) |
| 2026-07-09 | 0.2.0 | - | Geração via LM Studio, embeddings bge-m3 e top_k default fixados; spec aprovada | ADR-0002 |
| 2026-07-09 | 0.1.0 | - | Criação inicial da spec | ADR-0001 |
