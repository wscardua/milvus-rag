# Contrato — Consulta e Citações

Entre Django (UI) e FastAPI (`POST /query`).

## Requisição

- `question`: string
- `filters?`: filtros **opcionais** por metadado — `squad` / `delivery_process` (ADR-0007), `category`, `doc_type`, `tags`. Sem filtro, a busca é global.
- `top_k?`: número de chunks a recuperar (**default: 5**)

Parâmetros de retrieval: `top_k` default 5; abaixo de um **limiar de similaridade** (COSINE, valor a calibrar) a API responde "sem contexto suficiente" em vez de gerar. Geração feita pelo LM Studio (API OpenAI-compatível).

## Resposta

- `answer`: texto gerado
- `citations[]`: lista com
  - `document_id`
  - `chunk_id`
  - `snippet` (trecho de origem)
  - `score` (similaridade)
- `linked_flow[]` (ADR-0008): documentos vinculados considerados na expansão do contexto — `source_document_id`, `target_document_id`, `link_type`, e flag `included` (false quando excluído por `substitui`).

## Regras

- Toda resposta deve trazer ao menos as citações dos chunks usados (grounding).
- Retrieval faz **expansão de 1 salto** por vínculos (ADR-0008): inclui alvos de `esclarece`/`complementa`/`precede`; **exclui** alvos de `substitui` (obsoletos). O `linked_flow[]` informa o fluxo à UI.
- Se não houver contexto suficiente, a API deve indicar isso em vez de alucinar.
- A UI exibe as citações e o fluxo sem recalcular nada.
