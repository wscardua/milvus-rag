---
id: FEAT-MCP-001
title: Servidor MCP de Consulta ao Acervo
version: 0.3.0
status_spec: aprovada
status_impl: implementada
owner: -
created: 2026-07-09
updated: 2026-07-11
contracts: [query-and-citations, upload-and-metadata, organization-admin]
depends_on: [FEAT-QUERY-001]
adrs: [ADR-0005, ADR-0007, ADR-0015]
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
- Filtros por metadado: `squad`, `delivery_process`, `category`, `doc_type` e, a partir do WORK-010, `delivery_phase`/`tags` (ADR-0015) — nos mesmos filtros aceitos por `query-and-citations`.
- **Tools de listagem/lookup (WORK-010):** `list_squads`, `list_delivery_processes`, `list_categories`, `list_doc_types`, `list_delivery_phases`, `list_tags` — proxy fino dos GETs de apoio da API (contrato `organization-admin`), para o agente resolver **nome→id** (ex.: nome da squad → UUID) antes de montar `filters` nas tools de consulta. Sem esses lookups, um agente que só conhece nomes não consegue filtrar por `squad`/`delivery_process` (que exigem UUID).
### Fora de escopo
- Ingestão/upload via MCP (por ora só consulta; upload permanece na UI/API).
- Autenticação/autorização por agente (evolução futura).
- Filtro de `tags` com semântica AND (ver FEAT-QUERY-001 §3) — herdado da API.

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
- `retrieve_chunks(question, filters?, top_k?)` → apenas trechos relevantes, sem geração (via `POST /retrieve`).
- `list_squads()` → squads (`id`, `name`, ...) via `GET /squads` (WORK-010).
- `list_delivery_processes(squad_id?)` → processos de delivery, filtrável por squad, via `GET /delivery-processes` (WORK-010).
- `list_categories()` → categorias via `GET /categories` (WORK-010).
- `list_doc_types()` → lista fechada de `doc_type` via `GET /doc-types` (WORK-010).
- `list_delivery_phases()` → lista fechada de fases de delivery via `GET /delivery-phases` (WORK-010, ADR-0015).
- `list_tags()` → tags distintas do acervo via `GET /tags` (WORK-010, ADR-0015).
### Fluxos alternativos e de erro
- API indisponível → erro claro ao agente (não inventar resposta).
- Sem resultados no filtro → indicar acervo vazio para o recorte.

## 6. Regras de domínio
- O MCP **não** implementa retrieval nem fala com Milvus/Postgres — só chama a API.
- Respostas repassadas ao agente preservam as citações (grounding).
- Contratos reusados: `query-and-citations`, `upload-and-metadata`, `organization-admin`.
- Filtros que exigem id (`squad`, `delivery_process`) só funcionam se o agente já resolveu o nome para o UUID via a tool de lookup correspondente — a docstring de cada tool de consulta instrui isso explicitamente.

## 7. Contratos e integrações
- Consome `POST /query`, `POST /retrieve`, `GET /documents`, `GET /documents/{id}`, `GET /squads`, `GET /delivery-processes`, `GET /categories`, `GET /doc-types`, `GET /delivery-phases`, `GET /tags` (organization-admin).
- Depende do `API_BASE_URL` da API (configurável por ambiente; dev local `http://localhost:8001`).
- Implementação em `apps/mcp/app/`: `server.py` (FastMCP/stdio), `client.py` (HTTP + tradução de filtros), `config.py`.

## 8. Dados e persistência
- Nenhuma persistência própria; estado vive na API/Postgres/Milvus.

## 9. Segurança, privacidade e riscos
- POC local sem auth; expor o MCP amplia a superfície de acesso ao acervo — restringir a rede local.
- Respostas podem conter PII dos documentos; citações permitem auditoria da origem.

## 10. Critérios de aceite
- [x] `search_documents` retorna resposta com citações para uma pergunta com acervo indexado.
- [x] `list_documents`/`get_document` refletem os documentos e filtros por categoria.
- [x] Com a API fora do ar, a tool retorna erro explícito (sem alucinar).
- [x] `retrieve_chunks` devolve trechos + score sem geração (via `POST /retrieve`).
- [x] Tools de lookup (`list_squads`/`list_delivery_processes`/`list_categories`/`list_doc_types`/`list_delivery_phases`/`list_tags`) retornam as listas da API (WORK-010) — `test_client_mapping.py` (9 casos novos, proxy 1:1 parametrizado).
- [x] `search_documents`/`retrieve_chunks`/`list_documents` repassam `delivery_phase`/`tags` corretamente para a API (WORK-010, ADR-0015) — tradução testada em `test_client_mapping.py`; a correção do filtro em si é responsabilidade de FEAT-QUERY-001 (já validada lá). Só alcança documentos já reprocessados (reindexação manual/recomendada — ver Lacunas conhecidas).

## 11. Testes esperados
- **Unitário:** mapeamento tool → chamada HTTP; tradução de filtros; as 6 tools de lookup (`list_squads`/`list_delivery_processes`/`list_categories`/`list_doc_types`/`list_delivery_phases`/`list_tags`) mapeiam 1:1 para o GET correspondente, sem transformação de dados (proxy fino — `apps/mcp/tests/test_client_mapping.py`).
- **Integração:** MCP ↔ API FastAPI (mock ou API real) devolvendo citações; `list_delivery_processes(squad_id=...)` repassa o filtro; tools de consulta aceitando `delivery_phase`/`tags` em `filters` e repassando ao `POST /query`/`POST /retrieve` sem alterar a semântica.
- **Fluxo:** agente → tool → resposta com citações; agente resolve nome→id via `list_squads`/`list_delivery_processes` antes de filtrar `search_documents` por `squad`/`delivery_process` (fluxo que hoje é impossível — não há como o agente descobrir o UUID).
- **Avaliação (RAG):** herdada de FEAT-QUERY-001 (a qualidade vem da API).
- **Regressão:** contratos `query-and-citations`, `upload-and-metadata` e `organization-admin`; as 4 tools existentes (`search_documents`/`retrieve_chunks`/`list_documents`/`get_document`) continuam funcionando sem os novos filtros informados (retrocompat — `filters` continua opcional).

## 12. Dependências
- FEAT-QUERY-001 (retrieval + geração na API).
- SDK MCP (Python) e cliente HTTP.

## 13. Decisões relacionadas (ADRs)
- ADR-0005 — MCP como cliente HTTP da API. ADR-0007 — organização squad/processo (origem dos filtros por id). ADR-0015 — filtros por `delivery_phase`/`tags` no Milvus via campo dinâmico, sem drop/recriação da coleção.

## 14. Pendências e questões em aberto
- ~~Definir transporte padrão~~ → **resolvido (WORK-004): `stdio` como default; HTTP/Streamable fica como evolução (POC local, sem auth).**
- ~~Decidir se `retrieve_chunks` reusa `POST /query` com flag~~ → **resolvido (WORK-004): endpoint dedicado `POST /retrieve`, sem geração — evita acoplar dois contratos (ADR-0005, refinamento).**
- Política de auth por agente e transporte de produção (HTTP/Streamable) seguem como evolução futura.
- ~~Tools `list_delivery_phases`/`list_tags` e o filtro por `delivery_phase`/`tags` dependiam do ADR-0015 sair de `proposta` para `aceita`~~ → **resolvido: ADR-0015 `aceita`** (campo dinâmico, sem drop/recriação da coleção). Falta só o spike técnico do ADR (confirmar `LIKE` sobre campo dinâmico) antes de codar essas tools.

## 15. Histórico de atualizações
| Data | Versão | Autor | Mudança | Ref (workflow/ADR) |
|---|---|---|---|---|
| 2026-07-11 | 0.3.0 | - | 6 tools de lookup (`list_squads`/`list_delivery_processes`/`list_categories`/`list_doc_types`/`list_delivery_phases`/`list_tags`) para o agente resolver nome→id antes de filtrar; filtros de consulta ganham `delivery_phase`/`tags` (ADR-0015). Implementado e testado: pytest 15 (apps/mcp) | WORK-010, ADR-0007, ADR-0015 |
| 2026-07-09 | 0.2.0 | - | Implementação: `apps/mcp/` (FastMCP/stdio, 4 tools) + endpoint `POST /retrieve` na API. Pendências §14 resolvidas (transporte stdio; `retrieve_chunks` via endpoint dedicado) | WORK-004, ADR-0005 |
| 2026-07-09 | 0.1.0 | - | Criação da spec do servidor MCP de consulta | ADR-0005 |
