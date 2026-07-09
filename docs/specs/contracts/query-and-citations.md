# Contrato — Consulta e Citações

Entre Django (UI) e FastAPI (`POST /query`).

## Requisição

- `question`: string
- `filters?`: filtros por metadado (ex.: `doc_type`, `tags`)
- `top_k?`: número de chunks a recuperar (**default: 5**)

Parâmetros de retrieval: `top_k` default 5; abaixo de um **limiar de similaridade** (COSINE, valor a calibrar) a API responde "sem contexto suficiente" em vez de gerar. Geração feita pelo LM Studio (API OpenAI-compatível).

## Resposta

- `answer`: texto gerado
- `citations[]`: lista com
  - `document_id`
  - `chunk_id`
  - `snippet` (trecho de origem)
  - `score` (similaridade)

## Regras

- Toda resposta deve trazer ao menos as citações dos chunks usados (grounding).
- Se não houver contexto suficiente, a API deve indicar isso em vez de alucinar.
- A UI exibe as citações sem recalcular nada.
