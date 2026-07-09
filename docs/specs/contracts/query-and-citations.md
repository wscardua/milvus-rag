# Contrato — Consulta e Citações

Entre Django (UI) e FastAPI (`POST /query`, `POST /query/{query_id}/feedback`) e entre o servidor MCP e FastAPI (`POST /retrieve`, ADR-0005).

## Requisição

- `question`: string
- `filters?`: filtros **opcionais** por metadado — `squad` / `delivery_process` (ADR-0007), `category`, `doc_type`, `tags`. Sem filtro, a busca é global.
- `top_k?`: número de chunks a recuperar (**default: 5**)

Parâmetros de retrieval: `top_k` default 5; abaixo de um **limiar de similaridade** (COSINE, valor a calibrar) a API responde "sem contexto suficiente" em vez de gerar. Geração feita pelo LM Studio (API OpenAI-compatível).

## Resposta

- `query_id` (ADR-0011): id do `query_log` desta consulta — âncora do feedback.
- `answer`: texto gerado
- `insufficient_context`: bool (true quando abaixo do limiar → sem resposta)
- `citations[]`: lista com
  - `document_id`
  - `chunk_id`
  - `snippet` (trecho de origem)
  - `score` (similaridade)
- `linked_flow[]` (ADR-0008): documentos vinculados considerados na expansão do contexto — `source_document_id`, `target_document_id`, `link_type`, e flag `included` (false quando excluído por `substitui`).

## Feedback (👍/👎) — ADR-0011

- `POST /query/{query_id}/feedback` com `{ "rating": "up" | "down" }` → registra o voto no `query_log` (`rating` 1/-1, `rating_at`). `204` em sucesso; `404` se o `query_id` não existir; `422` para `rating` inválido.
- **Toda** consulta é registrada no `query_log` (não só as votadas), com métricas de tuning (scores, modelos, params de chunking, `latency_ms`) — ver ADR-0011.
- A UI envia o voto via fetch (proxy Django); é opcional e não bloqueia a consulta.

## Retrieval puro — `POST /retrieve` (ADR-0005 / FEAT-MCP-001)

Endpoint dedicado para recuperar **apenas os trechos relevantes, sem geração** — para um agente montar o próprio prompt (tool `retrieve_chunks` do MCP). Mantido **separado** do `POST /query` (que gera resposta + citações) para não acoplar dois comportamentos num só contrato.

- **Requisição:** `question` (string), `filters?` (mesmos de `/query`), `top_k?` (default 5).
- **Resposta:**
  - `insufficient_context`: bool (true quando nada supera o limiar de similaridade).
  - `chunks[]`: `document_id`, `chunk_id`, `ordinal`, `text` (trecho completo), `score`.
- **Diferenças para `/query`:** não gera resposta, não faz expansão por vínculos (ADR-0008) e **não grava `query_log`** (não há feedback a ancorar). `422` para pergunta vazia; `502` em falha de índice/modelo.

## Regras

- Toda resposta deve trazer ao menos as citações dos chunks usados (grounding).
- Retrieval faz **expansão de 1 salto** por vínculos (ADR-0008): inclui alvos de `esclarece`/`complementa`/`precede`; **exclui** alvos de `substitui` (obsoletos). O `linked_flow[]` informa o fluxo à UI.
- Se não houver contexto suficiente, a API deve indicar isso em vez de alucinar.
- A UI exibe as citações e o fluxo sem recalcular nada.
