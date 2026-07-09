---
name: milvus-rag-spec-editor
description: Use esta skill para criar, derivar, traduzir, normalizar e atualizar as specs técnicas da POC de RAG a partir da visão funcional, preservando rastreabilidade, impacto controlado e a memória operacional enxuta do projeto.
---

# Milvus RAG Spec Editor

Use esta skill quando a tarefa principal for mexer nos documentos que orientam o desenvolvimento.

## Objetivo

Transformar a visão funcional do RAG em specs técnicas utilizáveis e mantê-las consistentes quando o produto ou o pipeline mudar.

## Fluxo padrão

1. Para mudança multi-documento, registrar/atualizar trabalho em `docs/specs/state/status.md`.
2. Ler a visão funcional em `docs/specs/product/overview.md`.
3. **Feature nova**: copiar `docs/specs/features/_TEMPLATE.md` para `docs/specs/features/<slug>.md` e preencher TODAS as seções (nunca deixe seção vazia — use "N/A" com justificativa). **Feature existente**: ler a spec alvo em `docs/specs/features/`.
4. Revisar contratos associados em `docs/specs/contracts/`.
5. Atualizar apenas os artefatos explicitamente impactados.
6. Revisar testes esperados quando o comportamento mudar.
7. **Versionar a spec**: incrementar `version`, atualizar `updated` e adicionar uma linha na seção **Histórico de atualizações** da própria spec.
8. Atualizar o changelog em `docs/specs/state/status.md` (coerente com o histórico da spec).
9. Se a mudança alterar fronteiras, o modelo de embeddings ou o schema, registrar decisão a partir de `docs/specs/decisions/_TEMPLATE-ADR.md` e referenciá-la no frontmatter `adrs` da feature.

## Regras

- Os docs são a fonte da verdade.
- Toda feature nova parte de `docs/specs/features/_TEMPLATE.md`; todo ADR novo parte de `docs/specs/decisions/_TEMPLATE-ADR.md`.
- Não reescreva features não impactadas.
- Preserve `id`, rastreabilidade de origem e o **Histórico de atualizações** da spec (nunca apague linhas — só adicione).
- Ao traduzir conteúdo, não perca o vínculo com a versão base.
- Quando houver incerteza sobre arquitetura, consulte `docs/specs/architecture/`.
- Mudanças de comportamento precisam revisar testes e estado antes de serem encerradas.

## Entradas principais

- `docs/specs/features/_TEMPLATE.md` (base de toda feature nova)
- `docs/specs/decisions/_TEMPLATE-ADR.md` (base de todo ADR novo)
- `docs/specs/product/overview.md`
- `docs/specs/features/`
- `docs/specs/contracts/`
- `docs/specs/decisions/`
- `docs/specs/state/status.md`

## Saídas esperadas

- specs por feature criadas ou ajustadas
- contratos revisados
- changelog atualizado em `status.md`
- impacto de implementação sinalizado
