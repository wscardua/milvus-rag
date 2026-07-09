---
name: milvus-rag-workflow-governor
description: Use esta skill para abrir, acompanhar, retomar, concluir ou reverter mudanças multi-documento da POC de RAG, evitando que spec, contratos, testes e estado operacional fiquem descasados. Mantém memória de trabalho leve e retomável.
---

# Milvus RAG Workflow Governor

Use esta skill quando a tarefa tocar mais de um artefato ou quando houver risco de deixar docs, testes, contratos e estado desalinhados.

## Objetivo

Governar processos de mudança de ponta a ponta na POC, mantendo memória operacional enxuta e permitindo retomada segura sem depender do histórico da conversa.

## Quando usar

- propor nova feature (novo formato de documento, nova estratégia de chunking/retrieval)
- alterar feature existente
- iniciar ou retomar implementação
- revisar testes de uma feature
- cancelar, substituir ou registrar bloqueio de uma mudança

## Fluxo padrão (leve, para POC)

1. Abrir ou atualizar uma entrada em `docs/specs/state/status.md` (seção **Trabalho em aberto**).
2. Registrar feature alvo, objetivo, etapa atual e artefatos afetados.
3. Executar as etapas na ordem de `references/process-map.md`.
4. Atualizar estado, changelog, testes, contratos e decisões conforme o que mudou.
5. Fechar a entrada como `concluido`, `bloqueado`, `cancelado` ou `substituido`.

## Regras

- Não deixe mudança multi-documento sem uma entrada em `status.md`.
- Não apague histórico para reverter; use reversão lógica (marque `cancelado`/`substituido`).
- Toda retomada precisa apontar a próxima ação objetiva.
- Se uma etapa ficar pendente, registre bloqueio em vez de fingir conclusão.
- Mudança que altera contrato entre Django e FastAPI, schema do Postgres ou o índice Milvus precisa atualizar spec, contratos, testes e estado juntos.

## Entradas principais

- `docs/specs/state/status.md`
- `docs/specs/features/`
- `docs/specs/contracts/`
- `docs/specs/decisions/`

## Saídas esperadas

- entrada de trabalho atualizada em `status.md`
- pendências e próxima ação explícitas
- docs, contratos, testes e estado sincronizados
