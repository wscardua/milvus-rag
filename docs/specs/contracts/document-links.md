# Contrato — Vínculos entre Documentos

Entre Django (UI: Detalhe e Upload) e FastAPI. Introduzido por ADR-0008. Gerencia o **fluxo de documentos vinculados** (direcionado e tipado), sempre dentro da mesma squad.

## Endpoints

- `GET /documents/{id}/links` → vínculos do documento (saída e entrada), com `link_type`, `ordinal`, documento alvo/fonte (`id`, `title`, `status`) e flag de expansão.
- `POST /documents/{id}/links` → cria vínculo. Body: `target_document_id`, `link_type` (`esclarece`|`complementa`|`precede`|`substitui`), `ordinal?`.
- `DELETE /documents/{id}/links/{link_id}` → remove vínculo.
- (Upload) o `POST /documents` pode aceitar `links[]` iniciais (mesmo formato), aplicados após criar o documento.

## Regras

- **Mesma squad:** `source` e `target` devem pertencer à mesma squad (via `delivery_process → squad`); caso contrário `422`.
- Sem auto-vínculo (`target ≠ source`); vínculo duplicado (`source`,`target`,`link_type`) é rejeitado (`409`).
- `link_type` restrito à lista fixa (ver [reference/taxonomy.md](../reference/taxonomy.md)).
- Semântica de expansão no retrieval é do contrato `query-and-citations` / ADR-0008 (a UI não decide expansão).
- Apagar um documento remove seus vínculos (cascade).
