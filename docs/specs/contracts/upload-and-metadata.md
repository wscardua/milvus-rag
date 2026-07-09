# Contrato — Upload e Metadados

Entre Django (UI) e FastAPI (`POST /documents`, `GET /documents`, `GET /documents/{id}`, `GET /documents/{id}/file`, `DELETE /documents/{id}`).

## Upload — requisição

- `file`: arquivo (multipart). **Tipos permitidos:** PDF, DOCX, TXT/Markdown, HTML, `.py`, XLS/XLSX. Tamanho máximo definido pela API.
- `metadata`: objeto com:
  - `delivery_process_id` (**obrigatório**, ADR-0007) — vincula o documento ao processo de delivery (e, por herança, à squad).
  - `title` (**opcional**, ADR-0007) — se vazio, a IA sugere na ingestão (fallback = nome do arquivo).
  - `author`, `tags[]`, `doc_type`.
  - `links[]` (**opcional**, ADR-0008) — vínculos iniciais (`target_document_id`, `link_type`); mesma squad.
- **Não** aceita `category`/`subcategory`/`summary` no upload — são sugeridos pela ingestão (ver `PATCH` abaixo).

## Upload — resposta

- `document_id`
- `status`: `pending` | `processing` | `indexed` | `failed`
- `metadata` normalizados (inclui `squad_id`/`delivery_process_id`)

## Edição de classificação (overrides) — ADR-0007

- `PATCH /documents/{id}` → altera os campos **sugeridos pela IA e editáveis pelo usuário**: `title`, `category_id`, `subcategory_id`, `summary`.
- A API marca `classification_source = user` quando há override.
- `subcategory_id` deve pertencer à `category_id` informada (taxonomia).
- Gestão de vínculos do documento é feita pelo contrato `document-links` (ADR-0008).

## Estado / listagem

- `GET /documents/{id}` → `document_id`, `status`, `metadata` (squad/processo, `category`/`subcategory`/`summary`, `classification_source`, `ingested_at`), `error?`, timestamps.
- `GET /documents?filtro` → lista paginada com filtros por metadado, incluindo `squad`, `delivery_process`, `category`, `doc_type`, `status`.

## Acesso ao arquivo — ADR-0010

- `GET /documents/{id}/file` → serve o arquivo original. Query `download=true` → `Content-Disposition: attachment` (baixar); padrão → `inline` (visualização). Nome de arquivo codificado por RFC 5987 (acentos). `404` se o documento ou o arquivo não existir.
- `storage_path` **não** é exposto no payload de metadados (fica server-side). A UI Django faz **proxy** deste endpoint — o browser nunca acessa o disco/porta da API diretamente.

## Exclusão — ADR-0010

- `DELETE /documents/{id}` → **hard delete**. Remove vetores no Milvus, a linha `document` (cascade em `chunk`, `ingestion_job`, `document_link`) e o arquivo em disco. `204` em sucesso; `404` se inexistente.
- `query_log` **não** é afetado (histórico de avaliação sobrevive à exclusão — ADR-0011).

## Regras

- A UI valida tipo/tamanho, `delivery_process_id` e demais obrigatórios antes de enviar; a API revalida.
- `status` é a única fonte de progresso de ingestão exibida na UI.
- Squad/processo e taxonomia são lidos via contrato `organization-admin`.
