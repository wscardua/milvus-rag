# ADR-0008 — Vínculos entre documentos e expansão de retrieval

## Contexto

Um trecho relevante pode estar num documento enquanto o **esclarecimento** (definição, pré-requisito, próximo passo do fluxo, versão que o substitui) vive em outro. Sem relacionar documentos, o retrieval trata cada documento isoladamente e a resposta pode ficar incompleta. O negócio pediu que a busca possa **seguir o fluxo de documentos vinculados**.

Isto é uma mudança de **schema estrutural** (nova relação) **e** de **estratégia de retrieval** (montagem de contexto) — ambos gatilhos de ADR.

## Decisão

### Relação `document_link` (auto-relação N:N em `document`)
- `id`, `source_document_id` (FK → `document`), `target_document_id` (FK → `document`), `link_type`, `ordinal` (ordem no fluxo), timestamps.
- **Direcionado e tipado** (aresta `source → target`).
- **Restrição de escopo:** `source` e `target` devem pertencer à **mesma squad** (validado na API, via `delivery_process → squad`). Vínculo entre squads é rejeitado.
- Sem auto-vínculo (`source ≠ target`); unicidade por (`source`, `target`, `link_type`).

### Tipos de vínculo (`link_type`) e política de expansão no retrieval
Fixos (ver também [reference/taxonomy.md](../reference/taxonomy.md)). Aresta `fonte → alvo`:

| Tipo | Semântica | Expansão (1 salto) |
|---|---|---|
| `esclarece` | o alvo esclarece/detalha a fonte | **inclui** o alvo no contexto |
| `complementa` | o alvo complementa a fonte | **inclui** |
| `precede` | a fonte antecede o alvo no fluxo (alvo = próximo passo) | **inclui** (segue o fluxo) |
| `substitui` | a fonte substitui o alvo (alvo é versão obsoleta) | **exclui/marca** o alvo — não entra no contexto |

### Uso no retrieval (FEAT-QUERY-001)
1. Retrieval vetorial normal (top-k no Milvus, com filtros).
2. **Expansão de 1 salto:** para os documentos dos chunks recuperados, seguir vínculos de tipos expansíveis (`esclarece`/`complementa`/`precede`) e adicionar chunks dos alvos ao conjunto de contexto (respeitando o limite de contexto e deduplicando).
3. Documentos alvo de `substitui` a partir de um documento recuperado são **excluídos** do contexto (conteúdo obsoleto não contamina a resposta).
4. A resposta **informa o fluxo**: `linked_flow[]` com os documentos vinculados considerados (e os excluídos por substituição).
- Expansão limitada a **1 salto** na POC (evita explosão de contexto/latência); profundidade maior exige novo ADR.

## Impacto

- **FEAT-QUERY-001**: retrieval passa a expandir por vínculos e a resposta informa o fluxo. Bump.
- **FEAT-WEB-001**: Detalhe e Upload gerenciam vínculos (tipo + alvo da mesma squad); Consulta exibe o fluxo. Bump.
- **Contratos**: `query-and-citations` ganha `linked_flow[]`; novo contrato `document-links` (criar/remover vínculos com validação de squad).
- **architecture/database.md**: nova tabela `document_link`.
- **Milvus**: inalterado — a expansão é resolvida no Postgres (grafo de vínculos) após o retrieval vetorial; o contrato do índice (ADR-0002) permanece intacto.
- **Custo/latência**: expansão de 1 salto adiciona uma consulta ao grafo + leitura de chunks; limitada e deduplicada.

## Alternativas rejeitadas

- **Vínculo bidirecional sem tipo**: perde a noção de fluxo/ordem e não distingue `substitui` (obsoleto) de esclarecimento. Rejeitado.
- **Expansão multi-salto (transitiva)**: risco de explosão de contexto e latência na POC. Rejeitado por ora (reavaliar com ADR se necessário).
- **Incluir documentos `substitui` no contexto**: contaminaria a resposta com conteúdo superado. Rejeitado — são excluídos/sinalizados.
- **Vínculo entre squads**: quebra a coerência organizacional e amplia o risco de trazer contexto irrelevante. Rejeitado — restrito à mesma squad.
- **Resolver a expansão via payload do Milvus**: misturaria grafo de relações com índice vetorial; o grafo vive melhor no Postgres. Rejeitado.

## Data

2026-07-09

## Status

aceita
