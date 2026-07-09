# Contrato — Upload e Metadados

Entre Django (UI) e FastAPI (`POST /documents`, `GET /documents`, `GET /documents/{id}`).

## Upload — requisição

- `file`: arquivo (multipart). **Tipos permitidos:** PDF, DOCX, TXT/Markdown, HTML, `.py`, XLS/XLSX. Tamanho máximo definido pela API.
- `metadata`: objeto com campos como `title`, `author`, `tags[]`, `doc_type`.

## Upload — resposta

- `document_id`
- `status`: `pending` | `processing` | `indexed` | `failed`
- `metadata` normalizados

## Estado / listagem

- `GET /documents/{id}` → `document_id`, `status`, `metadata`, `error?`, timestamps.
- `GET /documents?filtro` → lista paginada com filtros por metadado.

## Regras

- A UI valida tipo/tamanho e metadados obrigatórios antes de enviar; a API revalida.
- `status` é a única fonte de progresso de ingestão exibida na UI.
