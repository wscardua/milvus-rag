# ADR-0010 — Ciclo de vida do documento: exclusão e acesso ao arquivo

## Contexto

A POC permitia criar documentos (upload → ingestão) e editar classificação, mas não **excluir** um documento nem **acessar o arquivo original** depois do upload. Duas necessidades operacionais:

1. **Exclusão**: remover um documento salvo. Como cada documento gera `chunk` no Postgres e vetores no Milvus, excluir só a linha `document` deixaria **vetores órfãos** no índice — violando o invariante de arquitetura "cada vetor no Milvus referencia um chunk rastreável no Postgres". Exclusão cruza as três camadas (API → Postgres → Milvus + arquivo em disco), o que a torna um gatilho de ADR.
2. **Acesso ao arquivo**: visualizar/baixar o arquivo original. O arquivo vive em `data/uploads/` (fonte de verdade da API). A UI Django é **cliente** — não pode ler o disco. Logo precisa de um endpoint servido pela API, com a UI fazendo proxy.

## Decisão

### Exclusão — `DELETE /documents/{id}`
- Ordem determinística: **(1)** remove vetores no Milvus (`vectorstore.delete_by_document`), **(2)** remove a linha `document` no Postgres — o cascade de FK/ORM já remove `chunk`, `ingestion_job` e `document_link` —, **(3)** remove o arquivo físico (best-effort).
- Milvus antes do Postgres: se a remoção de vetores falhar, `document`/`chunk` seguem rastreáveis (nada de órfãos silenciosos). O passo de arquivo é o último porque a fonte de verdade relacional já foi removida.
- Exclusão é **hard delete** (sem soft-delete/versionamento na POC). `404` se o documento não existir.
- **`query_log` não é afetado** pela exclusão: o histórico de avaliação (perguntas, scores, feedback) precisa sobreviver à remoção dos documentos, então não há FK de `query_log` para `document`/`chunk` — os ids ficam como snapshot em JSONB (ver ADR-0011).

### Acesso ao arquivo — `GET /documents/{id}/file`
- Serve o arquivo com `content_disposition_type` **inline** (padrão, para visualização) ou **attachment** (`?download=true`). Nome de arquivo codificado por RFC 5987 (suporta acentos).
- `404` se o documento ou o arquivo em disco não existir. `storage_path` **não** é exposto no `DocumentOut` (fica server-side).
- A UI Django expõe **Visualizar** (modal com `<iframe>`, apenas para PDF/TXT/MD/HTML) e **Baixar** (attachment). O browser fala só com o Django, que faz **proxy** para este endpoint — o guardrail "Django é cliente" é preservado.

## Impacto

- **FEAT-UPLOAD-001**: ganha exclusão e acesso ao arquivo (bump). Antes "versionamento/reupload" era fora de escopo — continua; exclusão é hard delete.
- **FEAT-INGEST-001**: formaliza a limpeza de chunks + vetores na exclusão (bump).
- **FEAT-WEB-001**: Detalhe ganha botões Excluir/Visualizar/Baixar + modal; proxy de arquivo (bump).
- **Contrato `upload-and-metadata`**: novos `DELETE /documents/{id}` e `GET /documents/{id}/file`.
- **architecture/database.md**: documenta a regra de cascade (chunk + ingestion_job + document_link) e vetores na exclusão. **vector-index.md**: `delete_by_document` no ciclo de exclusão.
- **Milvus/contrato do índice (ADR-0002)**: inalterado (dim/métrica/coleção). Só se acrescenta uma operação de delete por `document_id` (já existente).

## Alternativas rejeitadas

- **Soft-delete (flag `deleted_at`)**: mantém vetores no índice (poluindo o retrieval) ou exige filtro em toda busca; complexidade desnecessária na POC. Rejeitado — hard delete.
- **UI lê `data/uploads/` direto / link direto para a API**: quebra o guardrail (Django é cliente) e acopla a UI ao layout de storage/porta da API. Rejeitado — proxy pela API.
- **Excluir Postgres antes do Milvus**: perderia o mapeamento `chunk_id`→vetor necessário caso a limpeza do índice fosse por chunk; e uma falha deixaria vetores órfãos sem rastro. Rejeitado — Milvus primeiro (delete por `document_id`).
- **FK de `query_log` para `document` com cascade**: apagar um documento apagaria seu histórico de avaliação. Rejeitado — snapshot desacoplado (ADR-0011).

## Data

2026-07-09

## Status

aceita
