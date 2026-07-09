---
name: milvus-rag-spec-orchestrator
description: Use esta skill para conduzir ou retomar a implementação da POC de RAG a partir das specs técnicas, contratos, arquitetura, testes e memória operacional, sem depender do histórico da conversa.
---

# Milvus RAG Spec Orchestrator

Use esta skill quando a tarefa principal for implementar ou retomar implementação guiada por specs.

## Objetivo

Conduzir a execução da feature a partir dos documentos corretos, mantendo dependências, fronteiras e estado do projeto em sincronia.

## Fluxo padrão

1. Verificar trabalho em aberto em `docs/specs/state/status.md`.
2. Ler o status de implementação na mesma `status.md`.
3. Ler a feature alvo em `docs/specs/features/`.
4. Ler contratos listados no frontmatter da feature.
5. Revisar arquitetura e testes relevantes.
6. Planejar implementação por camada (Django → FastAPI → PostgreSQL/Milvus).
7. Após a execução, atualizar estado e testes executados ou pendentes.

## Regras

- Não assuma comportamento fora do que está documentado.
- Respeite os limites entre `frontend-web` (Django), `backend-api` (FastAPI), `database` (PostgreSQL) e `vector-index` (Milvus).
- Siga a estrutura de diretórios de `docs/specs/decisions/ADR-0003-project-structure.md` (`apps/api/` domínio, `apps/web/` cliente, `ops/` infra).
- Toda spec segue `docs/specs/features/_TEMPLATE.md`; leia o **Histórico de atualizações** e `version` da spec para entender sua evolução antes de implementar.
- Se a spec estiver desatualizada, interrompa a improvisação e proponha ajuste documental primeiro (`milvus-rag-spec-editor`).
- Não conclua uma feature sem validar os critérios de aceite em `docs/specs/testing/`.

## Entradas principais

- `docs/specs/features/`
- `docs/specs/architecture/`
- `docs/specs/contracts/`
- `docs/specs/testing/`
- `docs/specs/state/status.md`

## Saídas esperadas

- sequência de implementação por camada
- checklist de dependências
- atualização de status da feature
