---
name: milvus-rag-test-engineer
description: Use esta skill para implementar, revisar e executar testes concretos da POC de RAG — backend FastAPI, UI Django, contratos, PostgreSQL, indexação/busca no Milvus, fluxos de ingestão/consulta e avaliação de retrieval — a partir da estratégia de testes e dos critérios de aceite.
---

# Milvus RAG Test Engineer

Use esta skill quando a tarefa for transformar estratégia de testes em testes executáveis ou revisar evidência real de qualidade.

## Objetivo

Implementar e validar testes práticos para backend, UI e pipeline de RAG, mantendo aderência às specs, contratos e riscos de regressão.

## Fluxo padrão

1. Verificar trabalho em aberto em `docs/specs/state/status.md`.
2. Ler feature alvo, contratos e `docs/specs/testing/`.
3. Ler a saída esperada de `milvus-rag-test-strategy`.
4. Identificar testes de domínio/API, persistência, indexação/busca, fluxo e avaliação de retrieval.
5. Implementar ou revisar testes executáveis conforme a stack existente.
6. Executar testes aplicáveis ou registrar pendência objetiva.
7. Atualizar estado e changelog em `status.md` com evidência.

## Regras

- Teste deve verificar comportamento observável, contrato ou risco real.
- Evite testes acoplados a detalhes frágeis de implementação sem ganho claro.
- Backend deve cobrir domínio, endpoints, persistência, integração com o Milvus e erros relevantes.
- Ingestão deve cobrir extração, chunking e idempotência de reprocessamento.
- Retrieval deve ter avaliação sobre um conjunto fixo (recall/precisão) e checagem de grounding das citações.
- UI Django deve cobrir upload, validação de metadados, renderização e fluxos críticos.
- Quando um teste necessário não puder ser implementado, registre pendência em `status.md` (Lacunas conhecidas).

## Entradas principais

- `docs/specs/features/`
- `docs/specs/contracts/`
- `docs/specs/testing/`
- `docs/specs/state/status.md`
- código existente da POC

## Saídas esperadas

- testes executáveis ou plano de lacuna explícito
- evidência de execução ou bloqueio
- regressões cobertas por contrato e fluxo
- atualização de estado e changelog
