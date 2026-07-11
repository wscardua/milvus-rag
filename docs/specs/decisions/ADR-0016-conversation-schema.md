# ADR-0016 — Schema de conversação (`conversation` + `query_log.conversation_id`/`turn_index`)

## Contexto

`POST /query` é hoje stateless — cada pergunta é isolada, sem estado de conversa persistido. `query_log` (ADR-0011) é auditoria desnormalizada, sem FK para nada (snapshot em JSONB, sobrevive à exclusão de documentos): não modela sequência de turnos nem agrupamento de perguntas relacionadas. O negócio pediu perguntas de acompanhamento com contexto persistido (chat multi-turno), hoje explicitamente fora de escopo de FEAT-QUERY-001. Isto é mudança de **schema estrutural** — gatilho de ADR.

## Decisão

### Nova tabela `conversation`
- `id` (uuid, pk).
- `title` (nullable) — auto-gerado a partir da primeira pergunta (truncada) quando o cliente não envia um.
- `squad_id` (nullable, FK → `squad`) — **só valor de conveniência** para a UI pré-preencher o formulário de consulta; **não é filtro imposto pelo backend** (filtros continuam vindo em cada `POST /query`, como hoje).
- `created_at`, `updated_at` (tocado a cada turno gravado na conversa — usado para ordenar a sidebar por atividade recente).

### `query_log` ganha `conversation_id` e `turn_index`
- `conversation_id` (nullable, FK → `conversation`).
- `turn_index` (nullable, int) — **sempre calculado pelo servidor, nunca aceito do cliente** (evita gaps/duplicatas por bug ou requisição fora de ordem no cliente).
- Ambos **nullable**: ausência de `conversation_id` preserva o comportamento stateless atual (uso via MCP ou API direta continua funcionando sem qualquer mudança de contrato).

### Concorrência
- `turn_index` é calculado como `MAX(turn_index) + 1 WHERE conversation_id = :id` dentro da mesma transação que grava a linha de `query_log`, precedido por `SELECT ... FOR UPDATE` na linha de `conversation` — serializa turnos concorrentes na mesma conversa. Solução simples, suficiente para a POC (uso single-user); revisar se o padrão de uso evoluir para multi-cliente simultâneo na mesma conversa.

### Autenticação/multiusuário
- Fora de escopo nesta POC — não existe modelo de usuário no sistema hoje (nenhuma tabela/coluna de autenticação). `conversation` não tem `owner_id`. Se autenticação for introduzida no futuro, o isolamento de conversas por usuário é decisão de um ADR próprio, não bloqueia esta feature.

### Exclusão de conversa
- **Fora de escopo desta iteração.** Não há endpoint `DELETE /conversations/{id}`. Registrado explicitamente em "Fora de escopo" de FEAT-QUERY-001.

## Impacto

- **FEAT-QUERY-001**: bump de versão; novos endpoints `POST /conversations`, `GET /conversations` (lista paginada), `GET /conversations/{id}` (histórico); `POST /query` ganha `conversation_id` opcional e a resposta ecoa `conversation_id`/`turn_index` quando aplicável.
- **Migration Alembic nova**: tabela `conversation` + colunas `conversation_id`/`turn_index` em `query_log` (ambas nullable, sem backfill).
- **architecture/database.md**: nova entidade `conversation`, `query_log` ganha as 2 colunas.
- **FEAT-WEB-001**: nova tela de chat (sidebar de conversas + thread), cliente HTTP puro dos 3 endpoints novos.
- Sem mudança de schema/índice Milvus, sem mudança no contrato de embeddings.

## Alternativas rejeitadas

- **Guardar histórico só em `query_log`, sem tabela `conversation`**: perde metadado de conversa (título, timestamp de atividade) e obrigaria agregação cara (`GROUP BY conversation_id`) para listar conversas na sidebar a cada carregamento.
- **Estado de conversa em cache/sessão (não persistido)**: não sobrevive a restart do processo; não permite revisar histórico depois — requisito explícito da UI (thread de mensagens revisável).
- **`turn_index` calculado/enviado pelo cliente**: risco de gaps, duplicatas ou reordenação indevida se a UI enviar fora de ordem ou retry duplicar uma requisição.
- **`conversation` com `owner_id` desde já**: adiciona uma dimensão (autenticação) que não existe em nenhuma outra parte do sistema hoje — prematuro, sem caso de uso ainda.

## Data

2026-07-11

## Status

aceita
