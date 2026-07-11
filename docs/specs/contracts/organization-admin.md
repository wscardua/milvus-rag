# Contrato — Admin de Organização (Squad / Processo / Taxonomia)

Entre Django (UI de admin) e FastAPI. Introduzido por ADR-0007. Sustenta as telas de admin (Squads, Processos) e popula os selects de upload/consulta.

## Squads

- `GET /squads` → lista (`id`, `name`, `description`, contagem de processos/documentos).
- `POST /squads` → cria (`name` obrigatório e único, `description?`).
- `PATCH /squads/{id}` → edita (`name`, `description`).
- `DELETE /squads/{id}` → remove. **Bloqueado (`409`/`RESTRICT`)** se houver processos/documentos vinculados.

## Processos de Delivery

- `GET /delivery-processes?squad_id=` → lista filtrável por squad (`id`, `squad_id`, `name`, `description`, contagem de documentos).
- `POST /delivery-processes` → cria (`squad_id` obrigatório, `name` obrigatório e único dentro da squad, `description?`).
- `PATCH /delivery-processes/{id}` → edita (`name`, `description`).
- `DELETE /delivery-processes/{id}` → remove. **Bloqueado** se houver documentos vinculados.

## Taxonomia (leitura)

- `GET /categories` → lista de categorias (`id`, `name`).
- `GET /categories/{id}/subcategories` (ou `GET /subcategories?category_id=`) → subcategorias da categoria — alimenta os selects dependentes.

## Listas de apoio (lookup, leitura)

Listas fechadas/derivadas usadas para popular selects e resolver nome→id antes de filtrar (UI de Documentos/Consulta e tools do MCP, WORK-010):

- `GET /doc-types` → lista fechada de `doc_type` (`reference/taxonomy.md`).
- `GET /delivery-phases` → lista fechada de fases de delivery (ADR-0014, `reference/taxonomy.md`).
- `GET /tags` (ADR-0015) → tags distintas já usadas no acervo (`SELECT DISTINCT unnest(tags)`), para popular o campo de tag da UI/tool sem exigir digitação livre às cegas.

## Regras

- `delivery_process` sempre pertence a uma `squad`; `subcategory` sempre a uma `category`.
- Unicidade: `squad.name`; `delivery_process(name)` dentro da squad; `category.name`; `subcategory(name)` dentro da categoria.
- Exclusão com vínculos é bloqueada para preservar a rastreabilidade das citações (ADR-0007).
- A UI apenas consome; a API é a fonte da verdade da organização e da taxonomia.
