---
name: milvus-rag-test-strategy
description: Use esta skill para definir critérios de aceite, cenários de teste, avaliação de qualidade de retrieval e impacto de regressão das features da POC de RAG, com base nas specs técnicas e nos contratos compartilhados.
---

# Milvus RAG Test Strategy

Use esta skill quando a tarefa principal for definir, revisar ou atualizar testes esperados de uma feature.

## Objetivo

Garantir que mudanças de spec e implementação permaneçam cobertas por testes e critérios de aceite verificáveis, incluindo qualidade de retrieval e grounding das respostas.

## Fluxo padrão

1. Verificar trabalho em aberto em `docs/specs/state/status.md`.
2. Ler a feature alvo.
3. Ler os contratos afetados.
4. Revisar `docs/specs/testing/`.
5. Listar cenários unitários, de integração, de fluxo e de avaliação de RAG.
6. Mapear regressões esperadas.
7. Atualizar o changelog em `status.md` quando testes mudarem.

## Regras

- Testes acompanham comportamento e contratos.
- Mudanças de spec devem atualizar testes esperados.
- Cada feature deve declarar critérios de aceite objetivos nas seções **10. Critérios de aceite** e **11. Testes esperados** do `_TEMPLATE.md`.
- Para RAG, defina avaliação de qualidade: recall/precisão de retrieval em um conjunto fixo de perguntas e verificação de que a resposta cita chunks reais (grounding).
- Regressão deve ser mapeada pelo que pode quebrar (contratos, chunking, índice), não só pela tela afetada.
- Uma feature só vira `validada` com evidência de teste ou pendência justificada.

## Entradas principais

- `docs/specs/features/`
- `docs/specs/contracts/`
- `docs/specs/testing/`
- `docs/specs/state/status.md`

## Saídas esperadas

- cenários de teste (incl. avaliação de retrieval)
- matriz de cobertura
- regressões a proteger
- critérios de aceite revisados
