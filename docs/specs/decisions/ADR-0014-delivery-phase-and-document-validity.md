# ADR-0014 — Fase de delivery e vigência do documento (valid_until) com rebaixamento no retrieval

## Contexto
Dois metadados de ciclo de entrega faltavam ao `document` e afetam a qualidade da consulta:

1. **Fase de delivery** — a que etapa do fluxo de entrega o documento se refere (Discovery, refinamentos, desenvolvimento, testes, release, deploy). É um **eixo próprio**, distinto de:
   - `delivery_process` (ADR-0007): o *processo/iniciativa* dentro de uma squad (ex.: "Projeto X"), não a fase;
   - `category`/`subcategory` (taxonomia temática): o *assunto*;
   - `doc_type`: a *natureza/formato* do artefato.
   Sem esse eixo, não é possível filtrar "só o que é de Testes" ou "artefatos de Discovery" na listagem.

2. **Vigência (`valid_until`)** — muitos artefatos de delivery têm validade (uma especificação vigente até a próxima release, um runbook válido até certa data). Hoje o retrieval trata um documento **vencido** com a mesma relevância de um **vigente**: a busca é puramente por similaridade COSINE, sem noção de data. Isso faz a resposta citar conteúdo obsoleto como se fosse atual — risco direto de grounding enganoso.

Introduzir `valid_until` **muda a estratégia de retrieval** (a ordenação deixa de ser só similaridade) — gatilho obrigatório de ADR conforme `CLAUDE.md`. Ambos os campos são **mudança estrutural do schema `document`** — também gatilho de ADR. Consolidados aqui por serem, juntos, os metadados de ciclo de entrega do documento.

## Decisão

### Schema (`document`) — migration obrigatória
- `delivery_phase` `Mapped[str | None]` (nullable, `String(60)`). Lista **fechada** de fases (nova seção em [reference/taxonomy.md](../reference/taxonomy.md)):
  `Discovery` · `Refinamento Funcional` · `Refinamento Técnico` · `Desenvolvimento` · `Testes` · `Release` · `Deploy`.
- `valid_until` `Mapped[date | None]` (nullable, `Date`). `NULL` = sem validade (nunca vence).

Ambos **opcionais** — documentos já existentes permanecem com `NULL` (sem backfill). São **entrada do usuário** (não sugeridos pela IA), editáveis no upload e no detalhe (`PATCH /documents/{id}`). Como são opcionais, o `PATCH` não marca `classification_source=user` só por editá-los (eles não fazem parte da classificação temática da IA).

### Fase de delivery — só metadado/filtro (não entra no Milvus)
`delivery_phase` é filtrável na **listagem de documentos** (`GET /documents?delivery_phase=`, filtro no Postgres) e exibível na UI. **Não** entra no payload do Milvus nem nos filtros de `/query` — evita o problema de payload parcial (vetores já indexados não teriam o campo) e não há caso de uso pedido de "consultar só uma fase". Reavaliar se surgir necessidade (exigiria reindexação para popular o payload antigo).

### Vigência — rebaixamento (não exclusão) no retrieval
O retrieval **rebaixa** documentos vencidos em vez de excluí-los (mantém a possibilidade de grounding quando só há material vencido, mas nunca com a mesma relevância do vigente):

1. Busca vetorial no Milvus retorna hits por score COSINE (inalterado).
2. Para os documentos dos hits, carrega-se `valid_until` do Postgres.
3. Um documento é **vencido** quando `valid_until IS NOT NULL AND valid_until < hoje` (data, UTC).
4. Hits de documentos vencidos têm o score multiplicado por `retrieval_expired_score_factor` (default **0.5**, por env — ADR-0006). Os demais ficam intactos.
5. Os hits são **reordenados** pelo score ajustado; o limiar de "sem contexto suficiente" (`retrieval_min_score`) e a montagem de contexto/citações passam a usar o score ajustado.

Aplicado em `_search`, então vale para `POST /query` (com geração) **e** `POST /retrieve` (retrieval puro, FEAT-MCP-001). O `query_log.scores` grava o score **ajustado** (o efetivamente usado). Sem mudança no índice Milvus, no modelo ou na dimensão/métrica de embeddings (ADR-0002 intocado). O fator é multiplicativo (não um corte fixo) para degradar proporcionalmente e permitir env-tuning.

## Impacto
- **FEAT-UPLOAD-001**: upload e `PATCH` aceitam `delivery_phase` e `valid_until`; validação de `delivery_phase` contra a lista fechada (`422`) e de `valid_until` como data ISO (`422`).
- **FEAT-QUERY-001**: retrieval passa a rebaixar vencidos; contrato `query-and-citations` documenta o comportamento e o novo parâmetro de config.
- **FEAT-WEB-001**: upload/detalhe ganham os campos; listagem ganha filtro por fase (e por processo — ver WORK-007).
- `document`: **migration** adiciona `delivery_phase` e `valid_until` (ambos nullable, sem backfill).
- `config.py`: `retrieval_expired_score_factor` (novo, por env — ADR-0006).
- `reference/taxonomy.md`: nova seção com a lista fechada de fases de delivery.
- **Sem mudança no índice Milvus** (payload/dim/métrica), **sem mudança no contrato de embeddings** (ADR-0002).

## Alternativas rejeitadas
- **Excluir documentos vencidos do retrieval (hard filter)**: perde grounding quando o único material disponível está vencido; o usuário deixaria de ver "existe algo, porém vencido". Rejeitado — rebaixar preserva a informação com relevância menor.
- **Corte fixo no score (subtrair um delta)**: menos previsível entre faixas de score; o fator multiplicativo degrada proporcionalmente e é mais fácil de calibrar por env. Rejeitado.
- **`valid_until` no payload do Milvus com filtro por data**: o Milvus filtraria por expressão, mas exigiria reindexar todos os vetores existentes para popular o campo e não permite o rebaixamento *suave* (só corte). Rejeitado para a POC — o rebaixamento pós-busca no Postgres é suficiente e não mexe no índice.
- **`delivery_phase` como tabela de referência (FK)**: fase é uma lista curta e estável; uma coluna `String` validada contra a lista fixa (como `doc_type`) é suficiente e evita mais uma tabela/seed. Rejeitado para a POC.
- **Reaproveitar `delivery_process` para representar a fase**: são eixos ortogonais (um processo passa por várias fases); sobrecarregar o campo perderia ambos os cortes. Rejeitado.

## Data
2026-07-10

## Status
aceita
