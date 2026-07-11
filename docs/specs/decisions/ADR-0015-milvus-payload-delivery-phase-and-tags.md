# ADR-0015 — Extensão do payload Milvus para `delivery_phase` e `tags` (campo dinâmico, sem drop/recriação)

## Contexto
Hoje `/query` e `/retrieve` filtram a busca vetorial por `squad`, `delivery_process`, `category` e `doc_type` (`_PAYLOAD_FIELDS`/`_FILTER_MAP`, ADR-0007). Dois eixos de metadado do `document` ficaram de fora do índice:

- **`delivery_phase`** (ADR-0014): existe na coluna `document.delivery_phase` e já filtra `GET /documents`, mas a decisão original foi **não** levá-lo ao Milvus — "não há caso de uso pedido de consultar só uma fase" (ADR-0014, §"Fase de delivery"). Esse caso de uso agora existe (WORK-010): o usuário quer restringir a consulta em linguagem natural a uma fase específica.
- **`tags`** (`text[]` + GIN, ADR-0007): nunca chegou nem ao payload do Milvus nem a um filtro de leitura — não há `GET /tags` nem filtro de tags em `GET /documents`. O contrato `query-and-citations` já citava `tags` como filtro possível, mas a implementação nunca existiu (a tool `search_documents` do MCP chegou a anunciar o filtro e teve isso corrigido no review do WORK-004 — ver changelog 2026-07-09 — justamente por não haver suporte real).

`tags` é multivalorado por chunk (um documento pode ter várias tags), enquanto o payload do Milvus hoje só guarda campos escalares — precisa de um desenho explícito para o filtro funcionar com mais de uma tag por vez.

**Revisão desta versão do ADR (2026-07-11):** a primeira versão assumia que o schema da coleção Milvus era fixo após criado (`_ensure_collection` só roda `create_schema` na 1ª vez) e propunha dropar/recriar a coleção + reindexar o acervo inteiro numa tacada só, como gatilho de mudança de schema estrutural. A revisão de arquitetura (`milvus-rag-software-architect`) encontrou que a coleção é criada com **`enable_dynamic_field=True`** (`vectorstore.py:_ensure_collection`), rodando **Milvus 2.5.4 / pymilvus 2.5.4** — versões com suporte maduro a campo dinâmico (desde Milvus 2.2+): campos fora do schema declarado podem ser gravados no `upsert` e **filtrados via `expr` normalmente**, sem precisar declarar no schema nem recriar a coleção. Isso muda o mecanismo da decisão (abaixo), mas não a fronteira arquitetural nem a semântica dos filtros — `milvus-rag-architecture-guard` validou que o filtro continua construído só na FastAPI (`vectorstore.search`/`retriever._map_filters`), sem afetar Django/MCP.

## Decisão

### 1. `delivery_phase` — campo dinâmico, igualdade simples
- `upsert_chunks` (`vectorstore.py`) passa a incluir `delivery_phase` nas linhas de cada chunk, **fora de `_PAYLOAD_FIELDS`** (campo dinâmico — não precisa `schema.add_field`).
- `search()` ganha o mesmo tratamento de igualdade que os campos declarados (`delivery_phase == '<fase>'`), mesma sintaxe de `expr` — Milvus resolve campos dinâmicos pelo nome automaticamente quando `enable_dynamic_field=True`.
- `_FILTER_MAP` (`retriever.py`) ganha `"delivery_phase": "delivery_phase"`.
- Revisa parcialmente o ADR-0014 (§"Fase de delivery — só metadado/filtro"): a razão de não entrar no Milvus era "sem caso de uso"; o caso de uso passou a existir. O restante do ADR-0014 (vigência/rebaixamento) não muda.

### 2. `tags` — campo dinâmico com string delimitada + `LIKE`, semântica **OR**
- `upsert_chunks` grava `tags` (campo dinâmico) como string **delimitada por vírgula com sentinelas nas pontas** — ex.: 3 tags `["billing", "api", "v2"]` viram `",billing,api,v2,"`. O delimitador evita colisão com prefixos (`tag` não bate em `tag2`).
- Filtro por 1+ tags vira uma expressão Milvus com `OR` de `LIKE` por tag pedida: `(tags like "%,billing,%" or tags like "%,api,%")` — documento entra no resultado se tiver **qualquer uma** das tags do filtro (união, não interseção).
- **AND** (documento precisa ter todas as tags pedidas) fica **fora de escopo** desta POC — pode ser adicionado depois trocando `or` por `and` na expressão, sem mudar nada de schema/índice. Registrado em Pendências.
- `_FILTER_MAP`/`_map_filters` (`retriever.py`) ganham tratamento especial para `tags` (lista → expressão `OR`), diferente do `k: v` direto usado pelos demais campos.
- **Escaping obrigatório**: o valor de cada tag precisa do mesmo escaping já usado para `"`/`\` nos campos `==` (`vectorstore.py:75`), estendido para também escapar o delimitador `,` e o coringa `%` — evita que um valor de tag quebre a expressão do filtro Milvus (mesmo princípio de uma injeção de sintaxe, ainda que não seja SQL).
- **Ressalva de performance**: `LIKE '%...%'` com coringa nos dois lados é *scan* do campo (sem índice dedicado) — aceitável na escala desta POC, mesma característica que já existe hoje para os demais campos escalares filtráveis (nenhum tem índice próprio no Milvus). Não é uma escolha de produção.

### 3. Sem drop/recriação da coleção — spike de validação antes de generalizar
- **Não** é preciso dropar/recriar a coleção Milvus. `_ensure_collection` continua como está (`enable_dynamic_field=True` já ativo); só `upsert_chunks`/`search` mudam para ler/escrever os 2 campos novos.
- Documentos já indexados **antes** desta mudança simplesmente não têm `delivery_phase`/`tags` no payload — não aparecem em buscas filtradas por eles até serem reprocessados. Mesmo efeito "degrada sem quebrar" que a v1 deste ADR já previa, só que sem downtime nem evento único obrigatório.
- **Antes de generalizar**, validar com um **spike técnico rápido** (poucas linhas, parte da implementação — não bloqueia esta decisão): `upsert` de um chunk com um campo dinâmico de string + `search` com `filter` usando `LIKE` sobre esse campo, confirmando que o Milvus 2.5.4 filtra corretamente campo dinâmico com `LIKE` (equalidade em campo dinâmico é bem documentada; `LIKE` sobre string dinâmica é esperado funcionar nas versões recentes, mas não estava testado neste código antes desta decisão).
  - **Se o spike confirmar**: segue como decidido acima.
  - **Se o spike falhar** (Milvus não filtra `LIKE`/igualdade em campo dinâmico de forma confiável nesta versão): plano B é declarar `delivery_phase`/`tags` em `_PAYLOAD_FIELDS` (schema explícito), o que aí sim exige dropar/recriar a coleção + reindexação do acervo — a decisão original da v1 deste ADR volta a valer como fallback. Registrar a alternativa escolhida no changelog quando o spike rodar.

### 4. Reenfileiramento do acervo — recomendado, não bloqueante
- Reenfileirar `ingestion_job=pending` para documentos já `indexed`/`failed` continua sendo a forma de popular `delivery_phase`/`tags` nos chunks antigos — o pipeline de ingestão já é idempotente por documento (apaga chunks/vetores antigos antes de reinserir, ADR-0004/0009).
- Ao contrário da v1 deste ADR, isso **não é um requisito de deploy**: pode rodar em background, gradualmente, depois de liberar a feature — a busca funciona desde já para documentos novos/reprocessados, e os antigos só ficam de fora do filtro até serem reprocessados (comportamento degradado, não quebrado).
- Onde essa rotina de reenfileiramento em massa mora é decisão de implementação (fica dentro de `apps/api/app/`, reusando o mecanismo de fila existente — não um script solto fora da camada de domínio, conforme `architecture-guard`).

### 5. Canal Postgres (`GET /documents`, `GET /tags`) — mesma semântica OR, usando o GIN existente
- Filtro de tags em `GET /documents`: `tags && ARRAY[...]` (operador de sobreposição SQLAlchemy `Document.tags.overlap([...])`, usa o índice GIN já existente na coluna — ADR-0007) — mesma semântica OR do Milvus, para os dois canais de filtro não divergirem. Parametrizado via ORM, sem risco de injeção SQL.
- Novo `GET /tags`: `SELECT DISTINCT unnest(tags) FROM document ORDER BY 1` — popula o `<select>` da UI e a tool MCP `list_tags`.

## Impacto
- **FEAT-QUERY-001**: `/query` e `/retrieve` passam a aceitar `delivery_phase` e `tags` em `filters`; contrato `query-and-citations` documenta a semântica OR de `tags` e a igualdade simples de `delivery_phase`, e que o filtro só alcança documentos já reprocessados.
- **FEAT-MCP-001**: tools `search_documents`/`retrieve_chunks`/`list_documents` passam a aceitar os 2 filtros; novas tools `list_delivery_phases`/`list_tags`.
- **FEAT-WEB-001**: tela de Consulta ganha `<select name="delivery_phase">` e campo de tag(s); tela de Documentos ganha filtro de tags (`delivery_phase` já existia desde WORK-007).
- `apps/api/app/services/vectorstore.py`: `upsert_chunks` passa `delivery_phase`/`tags` (campos dinâmicos, fora de `_PAYLOAD_FIELDS`); `search()` monta a expressão de igualdade/`LIKE` para eles. **`_ensure_collection` não muda.**
- `apps/api/app/domain/ingestion/pipeline.py`: `upsert_chunks` (chamada) popula os 2 campos (serialização da lista de tags para a string delimitada).
- `apps/api/app/domain/retrieval/retriever.py`: `_FILTER_MAP`/`_map_filters` com tratamento especial para `tags` (expressão OR).
- `apps/api/app/api/documents.py`: filtro `tags` em `GET /documents`; novo `GET /tags`.
- **Sem migration no Postgres** — `document.delivery_phase` (ADR-0014) e `document.tags` (ADR-0007) já existem; a mudança é só em como o Milvus grava/filtra o payload.
- **Sem drop/recriação da coleção Milvus, sem reindexação obrigatória** — reenfileiramento do acervo é recomendado (background, gradual). Sem mudança no modelo/dimensão/métrica de embeddings (ADR-0002 intocado).

## Alternativas rejeitadas
- **Dropar/recriar a coleção declarando `delivery_phase`/`tags` em `_PAYLOAD_FIELDS`** (decisão da v1 deste ADR): tecnicamente mais "correta" (schema explícito, sem depender de campo dinâmico), mas exige janela de indisponibilidade no drop/recreate e reindexação do acervo inteiro como evento único bloqueante — custo desnecessário dado que `enable_dynamic_field=True` já resolve o mesmo resultado sem downtime. Rebaixada a **plano B**, a usar só se o spike do item 3 mostrar que campo dinâmico não filtra de forma confiável nesta versão do Milvus.
- **Filtrar `tags` só no Postgres pós-retrieval, no padrão do rebaixamento por vigência (ADR-0014)**: evitaria qualquer mudança no payload do Milvus para `tags`. Rejeitado porque é um **corte** (hard filter), não uma reordenação: aplicado depois do `top_k` do Milvus, poderia devolver menos resultados do que existem no acervo para aquela tag (o ANN já descartou hits por similaridade antes do filtro chegar). O rebaixamento de vigência não tem esse problema porque não descarta, só reordena.
- **Campo Milvus tipo `ARRAY` nativo com `ARRAY_CONTAINS`** (filtro nativo multivalorado, sem o hack de `LIKE`): mais correto semanticamente, mas depende de confirmar suporte estável na versão do Milvus/pymilvus em uso e exigiria declarar o campo no schema (voltando ao problema de drop/recriação). Preferida a string delimitada + `LIKE` em campo dinâmico, mais simples e sem tocar o schema; revisitar se o Milvus em uso suportar `ARRAY_CONTAINS` de forma estável sobre campo dinâmico também.
- **Tabela de tags normalizada (N:N)**: mesma razão do ADR-0007 — mais estrutura do que a POC precisa; `text[]`+GIN (Postgres) e string delimitada+`LIKE` (Milvus) atendem.
- **AND como semântica default do filtro de tags**: mais restritivo e menos intuitivo como primeira experiência (multi-seleção de tags costuma significar "qualquer uma destas" nos filtros de busca mais comuns). Rejeitado como default; fica registrado como evolução possível.
- **Excluir `delivery_phase` do Milvus e manter só no Postgres** (manter ADR-0014 como estava): rejeitado porque o caso de uso que faltava (filtrar a consulta em linguagem natural por fase) passou a existir — motivo original do ADR-0014 para essa exclusão.

## Data
2026-07-11 (revisado no mesmo dia — v1 assumia drop/recriação; v2 usa campo dinâmico após revisão de arquitetura)

## Status
aceita — fronteira validada por `milvus-rag-architecture-guard`; mecanismo (campo dinâmico vs. schema declarado) depende de um spike técnico de poucas linhas na implementação (§"Decisão", item 3), que não bloqueia a aceitação desta decisão, só decide entre o caminho principal e o plano B já documentado.
