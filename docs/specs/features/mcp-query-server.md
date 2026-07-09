---
id: FEAT-MCP-001
title: Servidor MCP de Consulta ao Acervo
version: 0.1.0
status_spec: aprovada
status_impl: nao_iniciada
owner: -
created: 2026-07-09
updated: 2026-07-09
contracts: [query-and-citations, upload-and-metadata]
depends_on: [FEAT-QUERY-001]
adrs: [ADR-0005]
---

# Feature — Servidor MCP de Consulta ao Acervo

## 1. Visão geral
Expõe o acervo vetorizado/categorizado a **outros agentes** via um servidor MCP (Model Context Protocol). O MCP é cliente HTTP da API FastAPI — reusa retrieval, geração e citações, sem duplicar lógica.

## 2. Contexto e problema
Além da UI Django, agentes precisam consultar os documentos salvos de forma programática e padronizada. MCP é o protocolo escolhido para essa interoperabilidade entre agentes.

## 3. Escopo
### Incluído
- Servidor MCP (`apps/mcp/`) expondo tools de consulta e navegação.
- Cliente HTTP para a API FastAPI (`base_url` configurável).
- Filtros por categoria/metadado (`doc_type`, `tags`).
### Fora de escopo
- Ingestão/upload via MCP (por ora só consulta; upload permanece na UI/API).
- Autenticação/autorização por agente (evolução futura).

## 4. Atores e pré-condições
- **Ator:** agentes MCP (ex.: outro Claude/assistente).
- **Pré-condições:** API FastAPI no ar com documentos indexados (FEAT-QUERY-001 operante).

## 5. Comportamento e fluxos
### Fluxo principal
1. Agente conecta ao servidor MCP (stdio por padrão; HTTP/SSE configurável).
2. Agente chama uma tool; o MCP traduz para chamada HTTP à API FastAPI.
3. A API executa retrieval/geração e devolve resposta + citações.
4. O MCP retorna o resultado ao agente.
### Tools expostas
- `search_documents(question, filters?, top_k?)` → resposta + citações (via `POST /query`).
- `list_documents(filters?)` → acervo por categoria/metadado (via `GET /documents`).
- `get_document(id)` → metadados e estado de um documento (via `GET /documents/{id}`).
- `retrieve_chunks(question, top_k?)` → apenas trechos relevantes, sem geração.
### Fluxos alternativos e de erro
- API indisponível → erro claro ao agente (não inventar resposta).
- Sem resultados no filtro → indicar acervo vazio para o recorte.

## 6. Regras de domínio
- O MCP **não** implementa retrieval nem fala com Milvus/Postgres — só chama a API.
- Respostas repassadas ao agente preservam as citações (grounding).
- Contratos reusados: `query-and-citations`, `upload-and-metadata`.

## 7. Contratos e integrações
- Consome `POST /query`, `GET /documents`, `GET /documents/{id}`.
- Depende do `base_url` da API (configurável por ambiente).

## 8. Dados e persistência
- Nenhuma persistência própria; estado vive na API/Postgres/Milvus.

## 9. Segurança, privacidade e riscos
- POC local sem auth; expor o MCP amplia a superfície de acesso ao acervo — restringir a rede local.
- Respostas podem conter PII dos documentos; citações permitem auditoria da origem.

## 10. Critérios de aceite
- [ ] `search_documents` retorna resposta com citações para uma pergunta com acervo indexado.
- [ ] `list_documents`/`get_document` refletem os documentos e filtros por categoria.
- [ ] Com a API fora do ar, a tool retorna erro explícito (sem alucinar).

## 11. Testes esperados
- **Unitário:** mapeamento tool → chamada HTTP; tradução de filtros.
- **Integração:** MCP ↔ API FastAPI (mock ou API real) devolvendo citações.
- **Fluxo:** agente → tool → resposta com citações.
- **Avaliação (RAG):** herdada de FEAT-QUERY-001 (a qualidade vem da API).
- **Regressão:** contratos `query-and-citations` e `upload-and-metadata`.

## 12. Dependências
- FEAT-QUERY-001 (retrieval + geração na API).
- SDK MCP (Python) e cliente HTTP.

## 13. Decisões relacionadas (ADRs)
- ADR-0005 — MCP como cliente HTTP da API.

## 14. Pendências e questões em aberto
- Definir transporte padrão de produção (stdio vs HTTP/SSE) e política de auth futura.
- Decidir se `retrieve_chunks` exige um endpoint dedicado na API ou reusa `POST /query` com flag.

## 15. Histórico de atualizações
| Data | Versão | Autor | Mudança | Ref (workflow/ADR) |
|---|---|---|---|---|
| 2026-07-09 | 0.1.0 | - | Criação da spec do servidor MCP de consulta | ADR-0005 |
