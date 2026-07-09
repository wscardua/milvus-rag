---
id: FEAT-WEB-001
title: Layout do Frontend (UI Django)
version: 0.4.0
status_spec: aprovada
status_impl: implementada
owner: -
created: 2026-07-09
updated: 2026-07-09
contracts: [upload-and-metadata, query-and-citations, organization-admin, document-links, logs-and-health]
depends_on: [FEAT-UPLOAD-001, FEAT-INGEST-001, FEAT-QUERY-001]
adrs: [ADR-0001, ADR-0002, ADR-0003, ADR-0007, ADR-0008, ADR-0010, ADR-0011]
---

# Feature — Layout do Frontend (UI Django)

> **Referência visual:** mock estático em [mocks/frontend-layout.html](../../../mocks/frontend-layout.html) (IBM Carbon Design System).

## 1. Visão geral
Define o layout e as telas da UI Django (cliente da API FastAPI): shell de navegação e sete telas — Documentos, Upload, Detalhe, Consulta, administração de Squads e Processos de Delivery, e **Logs & Saúde**. Entrega a jornada completa da POC como experiência coesa, no design system da IBM Cloud (Carbon), sem mover regra crítica para a UI.

## 2. Contexto e problema
As specs de domínio (upload, ingestão, consulta) existem, mas não há camada de apresentação. Além disso, o negócio introduziu uma organização por **Squad → Processo de Delivery → Documento** e metadados classificatórios sugeridos por IA (categoria/subcategoria/resumo) que o usuário pode revisar. Esta feature materializa essas telas e serve de referência visual e de fluxo para a implementação.

## 3. Escopo
### Incluído
- **Shell/layout base:** header de navegação (Carbon UI Shell), área de mensagens/notificações, identidade visual IBM Plex + tokens Carbon.
- **Tela Documentos (listagem):** tabela com título, squad/processo, categoria (sugerida por IA), `status` (badge), data de ingestão; filtros por squad, processo, categoria, `doc_type`, `status`; paginação. Atualização de `status` por **polling** de `GET /documents`.
- **Tela Upload:** seleção obrigatória de **Squad** e **Processo de Delivery** (selects dependentes); arquivo; `title` **opcional** (IA sugere); `author`, `doc_type`, `tags`; **vínculos iniciais opcionais** a documentos da mesma squad (tipo + alvo).
- **Tela Detalhe:** vínculo (squad/processo) + metadados do usuário; bloco **Título, classificação & resumo** com `title`, `category`/`subcategory` (selects de enum dependentes) e `summary` — **pré-preenchidos com a sugestão da IA e editáveis** (salvar overrides); **seção "Fluxo de documentos vinculados"** (adicionar/remover vínculos tipados da mesma squad; `substitui` marcado como excluído da busca); exibição de `error` quando `failed`. **Ações do documento (ADR-0010):** **Visualizar** (modal com `<iframe>` para PDF/TXT/MD/HTML), **Baixar** (arquivo original) e **Excluir** (com confirmação — remove chunks/vetores/arquivo).
- **Tela Consulta:** pergunta, filtros **opcionais** por squad/processo/categoria/`doc_type`, `top_k` (avançado, default 5); exibição da resposta com **citações** (snippet, documento, score), o **fluxo de documentos relacionados** (`linked_flow[]`) e o estado "sem contexto suficiente". **Feedback 👍/👎 (ADR-0011)** da resposta (via fetch; opcional).
- **Admin Squads:** CRUD de squads (nome, descrição).
- **Admin Processos de Delivery:** CRUD de processos vinculados a uma squad.
- **Tela Logs & Saúde (ADR-0011):** painel de saúde por serviço (Postgres/Milvus/LM Studio/worker) + fila de ingestão por estado; tabela de eventos do `system_log` com filtros por nível/componente. Consome `GET /health` e `GET /logs` (contrato `logs-and-health`).

### Fora de escopo
- Chunking, embeddings, retrieval, geração (domínio FastAPI / worker).
- Lógica de classificação por IA em si (é da ingestão — FEAT-INGEST-001).
- Autenticação/perfis avançados (apenas shell de usuário; auth detalhada fora da POC).
- Realtime (WebSocket/SSE) para status — a POC usa polling.

## 4. Atores e pré-condições
- **Atores:** usuário da UI (upload/consulta/edição de classificação); administrador (gestão de squads/processos).
- **Pré-condições:** API FastAPI disponível; contratos `upload-and-metadata` e `query-and-citations` estendidos (ver §7); schema com `squad`/`delivery_process`/taxonomia disponível (ver §8 e ADR a abrir).

## 5. Comportamento e fluxos
### Fluxo principal
1. (Admin) Cadastra squads e processos de delivery (telas de admin).
2. (Django Upload) Usuário escolhe **squad → processo** (obrigatórios), envia arquivo + metadados; UI valida tipo/tamanho e campos obrigatórios.
3. (FastAPI `POST /documents`) API revalida, cria `document` vinculado ao processo, enfileira ingestão (`ingestion_job=pending`).
4. (Worker) Ingestão processa e **sugere** `category`/`subcategory` (enum) e `summary`; ao concluir, `status=indexed` e `ingested_at` preenchido.
5. (Django Listagem/Detalhe) `status` evolui via polling; no Detalhe o usuário revisa/edita a classificação sugerida e salva overrides.
6. (Django Consulta) Usuário pergunta (com filtros opcionais de squad/processo/categoria/`doc_type`); UI exibe resposta + citações; ou o estado "sem contexto suficiente".

### Fluxos alternativos e de erro
- Squad/processo não selecionados → bloqueio de envio (obrigatórios).
- Tipo/tamanho de arquivo inválido → mensagem clara, sem criar documento (`400`/`413`/`415`).
- Ingestão `failed` → Detalhe exibe `error`.
- Consulta sem contexto suficiente → aviso, sem resposta fabricada.
- Tentar excluir squad/processo com documentos vinculados → bloqueado (`RESTRICT`).

## 6. Regras de domínio
- A UI é **cliente da API**: não faz chunking/embeddings/retrieval; apenas consome contratos.
- Todo documento pertence a exatamente **um processo de delivery** (e, por herança, a uma squad).
- `category`/`subcategory`/`summary` são **sugeridos pela IA e editáveis pelo usuário**; o valor final é do usuário quando houver override (`classification_source`).
- `status` exibido é a única fonte de progresso de ingestão (vem do `ingestion_job`).
- Toda resposta de consulta carrega citações (grounding) — a UI apenas exibe, sem recalcular.
- Conteúdo submetido é entrada não confiável (inclusive o `summary` gerado a partir dele).

## 7. Contratos e integrações
- **`upload-and-metadata`** (estendido, ADR-0007/0008): input com `delivery_process_id` (obrigatório), `title` opcional, `links[]` opcionais; `PATCH /documents/{id}` para overrides de `title`/`category`/`subcategory`/`summary`; saída/listagem com squad/processo/classificação.
- **`query-and-citations`** (estendido, ADR-0007/0008): `filters` incluindo `squad`/`delivery_process`; resposta com `linked_flow[]`.
- **`organization-admin`** (novo, ADR-0007): CRUD de `squad` e `delivery_process`; leitura de taxonomia para popular os selects dependentes.
- **`document-links`** (novo, ADR-0008): criar/listar/remover vínculos tipados (validação de mesma squad).
- **`upload-and-metadata`** (estendido, ADR-0010): `GET /documents/{id}/file` (visualizar/baixar via proxy Django) e `DELETE /documents/{id}` (excluir).
- **`query-and-citations`** (estendido, ADR-0011): `query_id` na resposta e `POST /query/{query_id}/feedback` (proxy Django via fetch).
- **`logs-and-health`** (novo, ADR-0011): `GET /health` (saúde por serviço + fila) e `GET /logs` (eventos com filtros).

## 8. Dados e persistência
Modelo (a formalizar no ADR de schema — ver §13):

```
squad(id, name·unique, description, timestamps)
  └─< delivery_process(id, squad_id→squad RESTRICT, name, description, timestamps, unique[squad_id,name])
        └─< document(id, delivery_process_id→delivery_process RESTRICT NOT NULL,
                     title, author, doc_type, tags text[],
                     original_filename, mime_type, size_bytes, storage_path,
                     category_id→category, subcategory_id→subcategory,   -- IA sugere / usuário edita
                     summary, classification_source[llm|user],
                     created_at, updated_at, ingested_at)
              ├─< chunk(id, document_id→document, ordinal, text, milvus_vector_id, token_count, ts)
              └─1:1 ingestion_job(id, document_id→document, state, error, attempts, timestamps)

category(id, name·unique) ─< subcategory(id, category_id→category, name, unique[category_id,name])
document_link(id, source_document_id→document, target_document_id→document, link_type, ordinal)  -- mesma squad (ADR-0008)
query_log(...)  -- opcional
```

Decisões de modelagem: taxonomia via **tabelas de referência** (não ENUM nativo); `tags` como **`text[]`** (índice GIN); exclusão de squad/processo com documentos → **`ON DELETE RESTRICT`**.

**Milvus (payload filtrável):** além de `document_id`/`chunk_id`/`doc_type`/`tags`/`author`, adicionar `squad_id`, `delivery_process_id`, `category`, `subcategory` para suportar os filtros da Consulta.

## 9. Segurança, privacidade e riscos
- PII em documentos e em `summary` gerado → tratar como dado sensível; citações permitem auditoria de origem.
- Prompt injection via conteúdo → mitigação é da ingestão/consulta (backend); a UI não relaxa isso.
- Exclusão de squad/processo bloqueada por `RESTRICT` protege a rastreabilidade das citações.
- UI não expõe endpoints internos nem acessa Milvus/Postgres direto.

## 10. Critérios de aceite
- [x] Layout base (Carbon) e navegação entre as 7 telas funcionam.
- [x] Upload exige squad + processo (dependentes) e valida tipo/tamanho antes de enviar.
- [x] Listagem mostra squad/processo, categoria (marcada como sugerida por IA) e `status` atualizando por polling.
- [x] Detalhe permite editar `title`/`category`/`subcategory`/`summary` pré-preenchidos pela IA e salvar overrides.
- [x] Detalhe/Upload permitem adicionar/remover vínculos tipados apenas a documentos da mesma squad; `substitui` é exibido como excluído da busca.
- [x] Consulta aplica filtros opcionais de squad/processo, exibe citações e o **fluxo de documentos relacionados** (`linked_flow[]`), além do estado "sem contexto suficiente".
- [x] Admin permite CRUD de squads e processos; exclusão com documentos vinculados é bloqueada.
- [x] Detalhe permite **Visualizar** (modal, tipos previewáveis), **Baixar** e **Excluir** o documento (ADR-0010).
- [x] Consulta permite dar **👍/👎** na resposta, registrado via API (ADR-0011).
- [x] Tela **Logs & Saúde** mostra o estado dos serviços e os eventos do `system_log` com filtros (ADR-0011).

## 11. Testes esperados
- **Unitário:** validação de formulários (obrigatoriedade de squad/processo, tipo/arquivo); dependência dos selects (squad→processo, categoria→subcategoria).
- **Integração:** UI ↔ contratos estendidos (`POST /documents`, `PATCH /documents/{id}`, `GET /documents`, `POST /query`, CRUD admin).
- **Fluxo:** admin cadastra squad/processo → upload → status até `indexed` → editar classificação → consulta com filtro por squad.
- **Avaliação (RAG):** N/A na UI (retrieval é do backend); a UI só exibe citações.
- **Regressão:** contratos `upload-and-metadata` e `query-and-citations`; comportamento dos filtros.

## 12. Dependências
- **Schema (ADR-0007/0008, aceitos):** tabelas `squad`, `delivery_process`, `category`, `subcategory`, `document_link` + colunas novas em `document` + payload Milvus. Propagado em `architecture/database.md` e `architecture/vector-index.md`.
- **FEAT-INGEST-001 (v0.6.0):** passo de classificação por IA (título + categoria/subcategoria + resumo).
- **FEAT-QUERY-001 (v0.4.0):** expansão por vínculos + `linked_flow[]`.
- **Contratos:** `upload-and-metadata`, `query-and-citations`, `organization-admin`, `document-links` (§7).
- **FEAT-UPLOAD-001 (v0.3.0):** upload com squad/processo, título opcional e vínculos.

## 13. Decisões relacionadas (ADRs)
- ADR-0001 (stack), ADR-0002 (embeddings/LLM), ADR-0003 (estrutura de diretórios).
- **ADR-0007** (aceito): organização `squad`/`delivery_process`, taxonomia, extensão de `document` (título/classificação/resumo/`ingested_at`) e payload Milvus.
- **ADR-0008** (aceito): vínculos entre documentos (`document_link`, fluxo tipado, mesma squad) e expansão de retrieval de 1 salto + `linked_flow[]`.
- **ADR-0010** (aceito): exclusão de documento e acesso ao arquivo (Visualizar/Baixar/Excluir no Detalhe; proxy do arquivo).
- **ADR-0011** (aceito): feedback 👍/👎 na Consulta e tela Logs & Saúde (contrato `logs-and-health`).

## 14. Pendências e questões em aberto
- Taxonomia (categorias/subcategorias) e enum de `doc_type` definidos em [reference/taxonomy.md](../reference/taxonomy.md) — os selects consomem essa lista.
- Detalhar payloads/erros dos contratos estendidos na implementação (`organization-admin`, `PATCH` de overrides).
- Decidir framework de CSS mínimo vs. Carbon oficial na implementação (mock usa tokens Carbon à mão).
- Confirmar limite de tamanho de upload (herda pendência de FEAT-UPLOAD-001).

## 15. Histórico de atualizações
| Data | Versão | Autor | Mudança | Ref (workflow/ADR) |
|---|---|---|---|---|
| 2026-07-09 | 0.4.0 | - | 7ª tela (Logs & Saúde); Detalhe ganha Visualizar/Baixar/Excluir; feedback 👍/👎 na Consulta; contrato `logs-and-health`. Spec aprovada | WORK-003, ADR-0010, ADR-0011 |
| 2026-07-09 | 0.3.0 | - | Título opcional/sugerido pela IA (editável); vínculos entre documentos no Detalhe/Upload; fluxo (`linked_flow[]`) na Consulta; contrato `document-links` | ADR-0007, ADR-0008 |
| 2026-07-09 | 0.2.0 | - | ADR-0007 aceito e propagado (schema, arquitetura, contratos); contrato `organization-admin` referenciado; dependências resolvidas | ADR-0007 |
| 2026-07-09 | 0.1.0 | - | Criação inicial da spec (6 telas Carbon; modelo Squad→Processo→Documento; classificação IA editável). Mock em `mocks/frontend-layout.html` | WORK-002 |
