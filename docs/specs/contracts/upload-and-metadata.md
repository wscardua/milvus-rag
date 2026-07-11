# Contrato — Upload e Metadados

Entre Django (UI) e FastAPI (`POST /documents`, `GET /documents`, `GET /documents/{id}`, `GET /documents/{id}/file`, `DELETE /documents/{id}`).

## Upload — requisição

- `file`: arquivo (multipart). **Tipos permitidos:** PDF, DOCX, TXT/Markdown, HTML, `.py`, XLS/XLSX, **PPT/PPTX**, **`.ipynb`**, **imagens** (`.png/.jpg/.jpeg/.gif/.bmp/.webp/.tiff`) — ADR-0002 (rev. 2026-07-10). Tamanho máximo definido pela API.
- `metadata`: objeto com:
  - `delivery_process_id` (**obrigatório**, ADR-0007) — vincula o documento ao processo de delivery (e, por herança, à squad).
  - `title` (**opcional**, ADR-0007) — se vazio, a IA sugere na ingestão (fallback = nome do arquivo).
  - `doc_type` (**obrigatório**, ADR-0013) — deve pertencer à lista em [reference/taxonomy.md](../reference/taxonomy.md); orienta o perfil de chunking na ingestão. Não é sugerido pela IA.
  - `delivery_phase` (**opcional**, ADR-0014) — fase do ciclo de entrega; deve pertencer à lista fechada em [reference/taxonomy.md](../reference/taxonomy.md) (§3).
  - `valid_until` (**opcional**, ADR-0014) — data ISO (`YYYY-MM-DD`) até quando o documento é vigente; após essa data ele é rebaixado no retrieval.
  - `author`, `tags[]`.
  - `links[]` (**opcional**, ADR-0008) — vínculos iniciais (`target_document_id`, `link_type`); mesma squad.
- **Não** aceita `category`/`subcategory`/`summary` no upload — são sugeridos pela ingestão (ver `PATCH` abaixo).
- **Erros:** `422` quando `doc_type` está ausente ou não pertence à lista em [reference/taxonomy.md](../reference/taxonomy.md) (ADR-0013); `422` quando `delivery_phase` não pertence à lista fechada ou `valid_until` não é data ISO válida (ADR-0014); `415` para extensão não suportada.

## Upload — resposta

- `document_id`
- `status`: `pending` | `processing` | `indexed` | `failed`
- `metadata` normalizados (inclui `squad_id`/`delivery_process_id`)

## Edição de classificação (overrides) — ADR-0007

- `PATCH /documents/{id}` → altera os campos **sugeridos pela IA e editáveis pelo usuário**: `title`, `category_id`, `subcategory_id`, `summary`, e também `delivery_phase`/`valid_until` (ADR-0014) e `tags[]` (ADR-0007, editável desde WORK-010 — antes só existia no upload) — todos entrada do usuário.
- A API marca `classification_source = user` quando há override de **classificação** (`title`/`category`/`subcategory`/`summary`). Editar `delivery_phase`/`valid_until`/`tags` **não** altera `classification_source` (não fazem parte da classificação temática da IA).
- `subcategory_id` deve pertencer à `category_id` informada (taxonomia). `delivery_phase` inválida ou `valid_until` não-ISO → `422`. `tags: []` limpa todas as tags do documento; a lista enviada **substitui** a anterior (não é incremental); valores são normalizados (trim, vazios descartados).
- **Sincronização com o Milvus (ADR-0015):** editar `category_id` (campo declarado) ou `delivery_phase`/`tags` (campos dinâmicos) de um documento **já indexado** resincroniza os chunks existentes no Milvus (`vectorstore.sync_document_fields`, sem reembeder/reextrair) — a edição de metadado não pode deixar o índice desatualizado. A sincronização acontece antes do commit no Postgres; se falhar, o `PATCH` falha inteiro.
- Gestão de vínculos do documento é feita pelo contrato `document-links` (ADR-0008).

## Estado / listagem

- `GET /documents/{id}` → `document_id`, `status`, `metadata` (squad/processo, `category`/`subcategory`/`summary`, `classification_source`, `delivery_phase`, `valid_until`, `ingested_at`), `error?`, timestamps.
- `GET /documents?filtro` → lista paginada com filtros por metadado: `squad_id`, `delivery_process_id`, `delivery_phase` (ADR-0014), `category_id`, `doc_type`, `status`.
  - **Paginação:** `limit` (default 50, máx 200) e `offset` (default 0). O total de itens do recorte (sem paginação) vem no cabeçalho de resposta **`X-Total-Count`**; o corpo permanece uma **lista** de documentos (retrocompatível). A UI usa o total para os controles de página.

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
