---
id: FEAT-UPLOAD-001
title: Upload e Metadados de Documento
version: 0.2.0
status_spec: aprovada
status_impl: nao_iniciada
owner: -
created: 2026-07-09
updated: 2026-07-09
contracts: [upload-and-metadata]
depends_on: []
adrs: [ADR-0001, ADR-0002]
---

# Feature — Upload e Metadados de Documento

## 1. Visão geral
Permite que o usuário envie documentos pela UI Django e defina metadados que orientam filtros, exibição e citações. É a porta de entrada do pipeline de RAG.

## 2. Contexto e problema
Sem uma entrada estruturada de documentos e metadados, não há o que ingerir nem como filtrar/citar depois. Esta feature dá o primeiro passo da jornada descrita em `product/overview.md`.

## 3. Escopo
### Incluído
- Formulário de upload de arquivo(s) com metadados (`title`, `author`, `tags`, `doc_type`).
- **Tipos aceitos:** PDF, DOCX, TXT/Markdown, HTML, `.py`, XLS/XLSX (ADR-0002).
- Criação do documento na API e disparo da ingestão.
- Exibição do estado de ingestão do documento.
### Fora de escopo
- Extração/chunking/embeddings (ver FEAT-INGEST-001).
- Versionamento de documento e reupload com histórico (fora da POC).

## 4. Atores e pré-condições
- **Ator:** usuário autenticado da UI Django.
- **Pré-condições:** API FastAPI disponível; tipos de arquivo e limite de tamanho definidos (ver Lacunas).

## 5. Comportamento e fluxos
### Fluxo principal
1. (Django) Usuário seleciona arquivo(s) e preenche metadados.
2. (Django) UI valida tipo/tamanho e campos obrigatórios.
3. (FastAPI `POST /documents`) API revalida, cria `document`, persiste metadados e dispara ingestão idempotente.
4. (FastAPI → Postgres) Cria `ingestion_job` com estado `pending`.
5. (Django) UI exibe o documento com estado `pending`/`processing`/`indexed`/`failed`.
### Fluxos alternativos e de erro
- Tipo/tamanho inválido → rejeição com mensagem clara (sem criar documento).
- Metadado obrigatório ausente → erro de validação.
- Falha ao criar documento na API → mensagem de erro; nada é persistido.

## 6. Regras de domínio
- A UI não processa conteúdo; apenas envia via contrato.
- Metadados são normalizados pela API antes de persistir.
- Upload trata o arquivo como entrada não confiável (tipo/tamanho validados; conteúdo só é processado na ingestão).

## 7. Contratos e integrações
- Contrato: `upload-and-metadata` (`POST /documents`, `GET /documents`, `GET /documents/{id}`).
- Erros previstos: `400` (validação), `413` (tamanho), `415` (tipo não suportado).

## 8. Dados e persistência
- `document`: arquivo + metadados (`title`, `author`, `tags`, `doc_type`, timestamps).
- `ingestion_job`: estado inicial `pending`, vínculo com `document`.

## 9. Segurança, privacidade e riscos
- Documentos podem conter PII → tratamento como dado sensível.
- Limite de tamanho e allowlist de tipos para mitigar abuso.
- Risco: arquivo malicioso; mitigação: validação de tipo e isolamento do processamento.

## 10. Critérios de aceite
- [ ] Upload com metadados válidos cria documento e inicia ingestão.
- [ ] Arquivo de tipo/tamanho inválido é rejeitado com mensagem clara e sem criar documento.
- [ ] Estado de ingestão é visível e atualiza até `indexed` ou `failed`.

## 11. Testes esperados
- **Unitário:** validação de metadados e de arquivo (tipo/tamanho).
- **Integração:** `POST /documents` cria `document` + `ingestion_job`.
- **Fluxo:** upload → estado final visível na UI.
- **Avaliação (RAG):** N/A (não há retrieval nesta feature).
- **Regressão:** contrato `upload-and-metadata`.

## 12. Dependências
- ADR-0001 (stack). A ingestão em si é FEAT-INGEST-001.

## 13. Decisões relacionadas (ADRs)
- ADR-0001 — stack da POC.

## 14. Pendências e questões em aberto
- Definir limite máximo de tamanho de arquivo (tipos já fixados em ADR-0002).

## 15. Histórico de atualizações
| Data | Versão | Autor | Mudança | Ref (workflow/ADR) |
|---|---|---|---|---|
| 2026-07-09 | 0.2.0 | - | Formatos de arquivo fixados; spec aprovada | ADR-0002 |
| 2026-07-09 | 0.1.0 | - | Criação inicial da spec | ADR-0001 |
