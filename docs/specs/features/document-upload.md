---
id: FEAT-UPLOAD-001
title: Upload e Metadados de Documento
version: 0.6.0
status_spec: aprovada
status_impl: implementada
owner: -
created: 2026-07-09
updated: 2026-07-10
contracts: [upload-and-metadata, document-links]
depends_on: []
adrs: [ADR-0001, ADR-0002, ADR-0007, ADR-0008, ADR-0010, ADR-0013, ADR-0014]
---

# Feature — Upload e Metadados de Documento

## 1. Visão geral
Permite que o usuário envie documentos pela UI Django e defina metadados que orientam filtros, exibição e citações. É a porta de entrada do pipeline de RAG.

## 2. Contexto e problema
Sem uma entrada estruturada de documentos e metadados, não há o que ingerir nem como filtrar/citar depois. Esta feature dá o primeiro passo da jornada descrita em `product/overview.md`.

## 3. Escopo
### Incluído
- **Vínculo obrigatório a Squad → Processo de Delivery** (ADR-0007) — selects dependentes.
- Formulário de upload de arquivo(s) com metadados: `title` (**opcional** — IA sugere, ADR-0007), `author`, `tags`.
- **`doc_type` obrigatório no upload (ADR-0013)** — orienta o perfil de chunking na ingestão (não é sugerido pela IA; ver [reference/taxonomy.md](../reference/taxonomy.md)).
- **Fase de delivery (`delivery_phase`) opcional (ADR-0014)** — eixo do ciclo de entrega (Discovery…Deploy), lista fechada; entrada do usuário, editável.
- **Vigência (`valid_until`) opcional (ADR-0014)** — data até quando o documento é vigente; documentos vencidos são **rebaixados** no retrieval (não excluídos).
- **Vínculos iniciais opcionais** a outros documentos da mesma squad (ADR-0008).
- **Tipos aceitos:** PDF, DOCX, TXT/Markdown, HTML, `.py`, XLS/XLSX, **PPT/PPTX**, **`.ipynb`** e **imagens** (`.png/.jpg/.jpeg/.gif/.bmp/.webp/.tiff`) — ADR-0002 (rev. 2026-07-10).
- Criação do documento na API e disparo da ingestão.
- Exibição do estado de ingestão do documento.
- **Exclusão do documento** (hard delete: remove chunks + vetores + arquivo — ADR-0010).
- **Visualização e download** do arquivo original (ADR-0010).
### Fora de escopo
- Extração/chunking/embeddings e sugestão de `title`/classificação (ver FEAT-INGEST-001).
- Versionamento de documento e reupload com histórico (fora da POC).
- Soft-delete/lixeira: a exclusão é definitiva.

## 4. Atores e pré-condições
- **Ator:** usuário autenticado da UI Django.
- **Pré-condições:** API FastAPI disponível; tipos de arquivo e limite de tamanho definidos (ver Lacunas).

## 5. Comportamento e fluxos
### Fluxo principal
1. (Django) Usuário escolhe **squad → processo** (obrigatórios), seleciona arquivo(s), preenche metadados (título opcional) e, opcionalmente, vínculos.
2. (Django) UI valida tipo/tamanho, `delivery_process_id` e campos obrigatórios.
3. (FastAPI `POST /documents`) API revalida, cria `document` (vinculado ao processo), aplica `links[]` (mesma squad), persiste metadados e dispara ingestão idempotente.
4. (FastAPI → Postgres) Cria `ingestion_job` com estado `pending`.
5. (Django) UI exibe o documento com estado `pending`/`processing`/`indexed`/`failed`.
### Fluxos alternativos e de erro
- Tipo/tamanho inválido → rejeição com mensagem clara (sem criar documento).
- Squad/processo ausente ou vínculo fora da squad → erro de validação (`422`).
- `doc_type` ausente ou inválido (fora da taxonomia) → rejeição `422` (ADR-0013).
- `delivery_phase` fora da lista fechada → rejeição `422`; `valid_until` em formato não-ISO → `422` (ADR-0014).
- Título vazio → aceito; IA sugere na ingestão (fallback = nome do arquivo).
- Falha ao criar documento na API → mensagem de erro; nada é persistido.

## 6. Regras de domínio
- A UI não processa conteúdo; apenas envia via contrato.
- Metadados são normalizados pela API antes de persistir.
- Upload trata o arquivo como entrada não confiável (tipo/tamanho validados; conteúdo só é processado na ingestão).

## 7. Contratos e integrações
- Contratos: `upload-and-metadata` (`POST /documents`, `GET /documents`, `GET /documents/{id}`, `GET /documents/{id}/file`, `DELETE /documents/{id}`) e `document-links` (vínculos iniciais, ADR-0008).
- Erros previstos: `400` (validação), `413` (tamanho), `415` (tipo não suportado), `422` (squad/processo ou vínculo inválido), `404` (documento/arquivo inexistente em file/delete).
- Acesso ao arquivo e exclusão passam pela API (ADR-0010); a UI faz **proxy** do arquivo (não lê o disco).

## 8. Dados e persistência
- `document`: arquivo + `delivery_process_id` (NOT NULL) + metadados (`title` opcional, `author`, `tags`, `doc_type`, `delivery_phase` opcional, `valid_until` opcional, timestamps).
- `document_link`: vínculos iniciais (mesma squad), se informados.
- `ingestion_job`: estado inicial `pending`, vínculo com `document`.

## 9. Segurança, privacidade e riscos
- Documentos podem conter PII → tratamento como dado sensível.
- Limite de tamanho e allowlist de tipos para mitigar abuso.
- Risco: arquivo malicioso; mitigação: validação de tipo e isolamento do processamento.

## 10. Critérios de aceite
- [x] Upload com metadados válidos cria documento e inicia ingestão.
- [x] Arquivo de tipo/tamanho inválido é rejeitado com mensagem clara e sem criar documento.
- [x] Estado de ingestão é visível e atualiza até `indexed` ou `failed`.
- [x] Excluir um documento remove sua linha, chunks (Postgres), vetores (Milvus) e o arquivo; reexclusão → `404`.
- [x] Visualizar abre o arquivo (PDF/TXT/MD/HTML) e Baixar entrega o arquivo original (nomes acentuados ok).
- [ ] Upload sem doc_type é rejeitado com 422.

## 11. Testes esperados
- **Unitário:** validação de metadados e de arquivo (tipo/tamanho).
- **Integração:** `POST /documents` cria `document` + `ingestion_job`.
- **Fluxo:** upload → estado final visível na UI.
- **Avaliação (RAG):** N/A (não há retrieval nesta feature).
- **Regressão:** contrato `upload-and-metadata`.

## 12. Dependências
- ADR-0001 (stack). A ingestão em si é FEAT-INGEST-001.

## 13. Decisões relacionadas (ADRs)
- ADR-0001 — stack da POC. ADR-0002 — formatos (rev. 2026-07-10: +PPTX/`.ipynb`/imagens). ADR-0007 — vínculo obrigatório squad/processo e título opcional (IA sugere). ADR-0008 — vínculos iniciais entre documentos. ADR-0010 — exclusão (cascade + Milvus + arquivo) e acesso ao arquivo (view/download via proxy). ADR-0014 — `delivery_phase` e `valid_until` (metadados de ciclo de entrega).

## 14. Pendências e questões em aberto
- Definir limite máximo de tamanho de arquivo (tipos já fixados em ADR-0002).

## 15. Histórico de atualizações
| Data | Versão | Autor | Mudança | Ref (workflow/ADR) |
|---|---|---|---|---|
| 2026-07-10 | 0.6.0 | - | `delivery_phase` e `valid_until` opcionais; novos formatos (PPTX/`.ipynb`/imagens) | WORK-007, ADR-0014, ADR-0002 (rev.) |
| 2026-07-10 | 0.5.0 | - | doc_type obrigatório no upload (orienta o perfil de chunking na ingestão) | WORK-006, ADR-0013 |
| 2026-07-09 | 0.4.0 | - | Exclusão de documento (hard delete: chunks+vetores+arquivo) e visualização/download do arquivo (via proxy) | WORK-003, ADR-0010 |
| 2026-07-09 | 0.3.0 | - | Vínculo obrigatório squad/processo; `title` opcional (IA sugere); vínculos iniciais entre documentos | ADR-0007, ADR-0008 |
| 2026-07-09 | 0.2.0 | - | Formatos de arquivo fixados; spec aprovada | ADR-0002 |
| 2026-07-09 | 0.1.0 | - | Criação inicial da spec | ADR-0001 |
