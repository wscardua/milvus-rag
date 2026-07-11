# ADR-0017 — Query condensation para retrieval multi-turno

## Contexto

Perguntas de acompanhamento numa conversa ("e quem é o responsável por isso?") não são autônomas o suficiente para embedding/busca direta no Milvus — o retrieval vetorial depende do texto literal da pergunta. Ao mesmo tempo, carregar os chunks recuperados no turno anterior diretamente no prompt do turno seguinte quebraria o **grounding obrigatório** do projeto: a citação de um turno anterior pode não ser mais a mais relevante para a pergunta atual, e o contexto acabaria citando algo que não foi de fato recuperado para esta pergunta. Isto é mudança de **estratégia de retrieval** — gatilho de ADR.

## Decisão

### Condensação condicional
- Antes de embutir/buscar no Milvus, **se `conversation_id` presente E `turn_index > 0`**, uma chamada LLM reescreve a pergunta de acompanhamento como pergunta autônoma, usando as **últimas 2-4 perguntas anteriores** da mesma conversa (busca em `query_log` por `conversation_id`, ordenado por `turn_index` desc, limit configurável).
- A primeira pergunta de uma conversa (`turn_index == 0`) **nunca** passa por condensação — já é autônoma por definição (não há histórico prévio).
- **Só as perguntas anteriores** entram no prompt de condensação, **não as respostas geradas** — reduz a superfície de prompt injection: respostas anteriores podem conter trechos citados de documentos (entrada não confiável), enquanto as perguntas do próprio usuário são uma superfície mais controlada.

### Falha degrada, não bloqueia
- Se a chamada de condensação falhar (LM Studio indisponível, erro do modelo etc.), degrada para a **pergunta crua** — mesmo padrão *best-effort* já usado em `_apply_classification`/`describe_image` (WORK-008) — e registra `eventlog.log_event("WARNING", "query", "llm_condensation_failed", ...)`, visível na tela Logs & Saúde (ADR-0011). A resposta ao usuário não é bloqueada.

### Retrieval por turno permanece independente
- Cada turno é recuperado e citado do zero a partir da pergunta condensada (ou crua, no primeiro turno/em caso de falha). Chunks do turno anterior **nunca** entram diretamente no prompt do turno seguinte — evita citação obsoleta e preserva o grounding por turno.

### Prompt final em 3 blocos
1. **Instruções de sistema** — grounding obrigatório, abstenção quando não houver contexto suficiente. Reafirmado a cada chamada — já é o comportamento natural hoje, pois cada requisição HTTP monta um prompt novo do zero (não há sessão persistida no LM Studio entre turnos), o que já mitiga a injeção de instrução persistente via histórico.
2. **Histórico condensado** — só para tom/coerência conversacional; explicitamente **não é fonte de verdade e não é citável**.
3. **Chunks recuperados neste turno** — única fonte de verdade, única fonte citável.

### Orçamento de contexto
- Troca o truncamento bruto de 8000 caracteres (`retriever.py:answer_query`) por um orçamento por **contagem de palavras** — a mesma aproximação de "tokens" já usada em todo o projeto para chunking (`pipeline.py: token_counts = [len(c.split()) for c in chunks]`, `config.chunk_size_words`). **Não introduz tokenizer real (ex.: tiktoken)** — manter consistência com a convenção existente em vez de misturar duas noções de "token" no mesmo código.
- O orçamento total é dividido entre histórico condensado (teto pequeno fixo, novo config) e chunks recuperados (o restante).

### Configuração/parametrização (reforça ADR-0006)
- A chamada de condensação reusa `app/services/llm.py` (mesmo cliente `lmstudio.client`, API compatível OpenAI) — a mesma peça que já torna trocar embeddings/chat por um provedor hospedado uma mudança de `.env`, não de código.
- Segue o padrão já usado para vision (`VISION_MODEL` distinto de `CHAT_MODEL`, mesmo `base_url` — ADR-0012): novo `condensation_model` (env `CONDENSATION_MODEL`), com **default = mesmo valor de `chat_model`** se não setado — permite usar um modelo mais barato/rápido só para condensação sem tocar no modelo de geração da resposta final.
- Nenhum endpoint, credencial ou nome de modelo fica hardcoded em `retriever.py` — tudo lido de `settings`, documentado em `.env.example`. Migrar do LM Studio local para um provedor hospedado (embedding e/ou chat e/ou condensação) continua sendo troca de `lm_studio_base_url`/`lm_studio_api_key`/`chat_model`/`condensation_model` no `.env`, sem mudança de código — mesma garantia que já vale para embeddings e chat hoje.

## Impacto

- **FEAT-QUERY-001**: bump de versão; `retriever.py` ganha a função de condensação (condicional a `conversation_id`+`turn_index>0`) e o cálculo de orçamento por palavras substitui o corte de 8000 caracteres.
- **Config nova** (`apps/api/app/config.py`, `.env.example`, ADR-0006): `condensation_model` e um teto de palavras para o histórico condensado (ex.: `history_budget_words`).
- **Latência/custo**: 1 chamada LLM adicional por turno de acompanhamento (não no primeiro turno de cada conversa) — mitigado por usar um modelo mais barato/rápido via `condensation_model` quando disponível.
- Sem mudança de schema/índice Milvus, sem mudança no modelo de embeddings.

## Alternativas rejeitadas

- **Carregar chunks do turno anterior direto no prompt do turno seguinte**: rejeitado — quebra o grounding (citação do turno anterior pode não ser mais a mais relevante para a pergunta atual, e o contexto citaria algo não recuperado para esta pergunta).
- **Buscar a pergunta de acompanhamento crua no Milvus, sem condensação**: rejeitado — recall ruim para perguntas elípticas ("e quem é o responsável por isso?" não tem embedding próximo de nada específico).
- **Incluir as respostas anteriores (não só as perguntas) no prompt de condensação**: rejeitado — amplia a superfície de prompt injection, já que respostas podem conter trechos citados de documentos (entrada não confiável).
- **Usar tokenizer real (ex.: `tiktoken`) para o orçamento de contexto**: rejeitado por ora — inconsistente com a aproximação por contagem de palavras já convencionada em todo o pipeline de chunking; reavaliar via ADR se a imprecisão se mostrar um problema prático.

## Data

2026-07-11

## Status

aceita
