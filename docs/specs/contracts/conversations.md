# Contrato — Conversas (chat multi-turno)

Entre Django (UI: tela de chat) e FastAPI. Introduzido por ADR-0016/ADR-0017 (FEAT-QUERY-001, WORK-012). Gerencia a persistência de conversas e o encadeamento de turnos consultados via `POST /query` (contrato `query-and-citations`).

## Endpoints

- `POST /conversations` → cria uma conversa. Body: `title?` (string; se ausente, gerado a partir da primeira pergunta feita nela), `squad_id?` (UUID, só conveniência de UI — não filtra o retrieval). Resposta: `id`, `title`, `squad_id`, `created_at`, `updated_at`.
- `GET /conversations` → lista conversas, paginado (mesmo padrão `X-Total-Count` de `GET /documents`/`GET /logs`), ordenado por `updated_at desc`. Cada item: `id`, `title`, `squad_id`, `created_at`, `updated_at`.
- `GET /conversations/{id}` → histórico da conversa: metadados da conversa + lista de turnos (a partir de `query_log` filtrado por `conversation_id`, ordenado por `turn_index`). Cada turno: `turn_index`, `question`, `answer`, `citations[]`, `linked_flow[]`, `insufficient_context`, `created_at`. `404` se a conversa não existir.
- `POST /query` com `conversation_id` (contrato `query-and-citations`) grava um novo turno na conversa — não há endpoint dedicado para "enviar mensagem"; é o mesmo `/query` de sempre, só que associado a uma conversa.

## Regras

- **`turn_index` é sempre calculado pelo servidor**, nunca aceito do cliente. Calculado como `MAX(turn_index) + 1` dentro da mesma transação que grava o turno em `query_log`, com lock de linha (`SELECT ... FOR UPDATE`) na `conversation` — serializa turnos concorrentes na mesma conversa.
- **Query condensation (ADR-0017):** para todo turno com `turn_index > 0`, a pergunta enviada em `POST /query` é reescrita internamente (autônoma) antes do retrieval, usando as últimas 2-4 perguntas anteriores da mesma conversa — **só perguntas, nunca respostas geradas** (superfície de prompt injection via histórico). O primeiro turno (`turn_index == 0`) nunca passa por condensação. Falha na condensação degrada para a pergunta crua (best-effort) e não é exposta ao cliente como erro.
- Cada turno é recuperado e citado **de forma independente** — grounding não é herdado de turnos anteriores.
- `conversation.squad_id` é opcional e não é aplicado como filtro pelo backend em `POST /query` — os filtros de cada consulta continuam vindo explicitamente no corpo de `/query`, como no uso stateless.
- Sem autenticação/isolamento por usuário nesta POC — qualquer cliente que conheça o `conversation_id` pode lê-la/postar nela (não há dono).
- **Sem endpoint de exclusão** (`DELETE /conversations/{id}`) nesta iteração — fora de escopo (ADR-0016).
- Uso stateless de `POST /query` (sem `conversation_id`) permanece 100% inalterado — este contrato é estritamente aditivo.
