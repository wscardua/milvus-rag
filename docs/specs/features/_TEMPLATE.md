<!--
TEMPLATE DE FEATURE SPEC — Milvus RAG (POC)

Como usar (IA/agente):
1. Copie este arquivo para docs/specs/features/<slug>.md (ex.: document-upload.md).
2. Preencha TODOS os campos do frontmatter e TODAS as seções. Remova os comentários <!-- ... --> ao concluir.
3. Nunca deixe uma seção vazia: se não se aplica, escreva "N/A" com uma linha de justificativa.
4. A cada alteração relevante, incremente `version`, atualize `updated` e adicione uma linha em "Histórico de atualizações".
5. Registre o mesmo evento no changelog de docs/specs/state/status.md e, se mudou fronteira/schema/índice, abra um ADR.

Objetivo do template: dar a visão necessária para entender a spec e seu histórico, e guiar o desenvolvimento assertivo pelas skills milvus-rag-*.
-->
---
id: FEAT-<AREA>-<NNN>            # ex.: FEAT-QUERY-001 — único e estável
title: <título curto da feature>
version: 0.1.0                    # incrementar a cada mudança relevante (semver simples)
status_spec: rascunho            # rascunho | em_revisao | aprovada | defasada_pela_spec
status_impl: nao_iniciada        # nao_iniciada | em_andamento | implementada | validada | defasada
owner: <responsável ou "-">
created: <AAAA-MM-DD>
updated: <AAAA-MM-DD>
contracts: []                    # ids de docs/specs/contracts/ (ex.: [query-and-citations])
depends_on: []                   # ids de outras features (ex.: [FEAT-INGEST-001])
adrs: []                         # ADRs relacionados (ex.: [ADR-0001])
---

# Feature — <título>

## 1. Visão geral
<!-- Em 2-4 linhas: o que a feature entrega e qual valor gera para o usuário. -->

## 2. Contexto e problema
<!-- O que motivou a feature. Qual dor/limitação ela resolve. Referencie product/overview.md se ajudar. -->

## 3. Escopo
### Incluído
<!-- Lista objetiva do que está dentro. -->
### Fora de escopo
<!-- O que explicitamente NÃO será feito agora (evita ambiguidade). -->

## 4. Atores e pré-condições
<!-- Quem usa (usuário, admin, job) e o que precisa estar verdadeiro antes (ex.: documento indexado). -->

## 5. Comportamento e fluxos
### Fluxo principal
<!-- Passo a passo numerado do caminho feliz, indicando a camada de cada passo (Django/FastAPI/Postgres/Milvus). -->
### Fluxos alternativos e de erro
<!-- Validações que falham, sem contexto suficiente, arquivo inválido, falha de ingestão, etc. -->

## 6. Regras de domínio
<!-- Regras que valem sempre (ex.: resposta sempre com citações; ingestão idempotente; conteúdo é entrada não confiável). -->

## 7. Contratos e integrações
<!-- Contratos consumidos/afetados (docs/specs/contracts/). Endpoints, payloads de entrada/saída e erros previstos. -->

## 8. Dados e persistência
<!-- Entidades/campos tocados no Postgres (document/chunk/ingestion_job/...) e no índice Milvus (coleção/payload). -->

## 9. Segurança, privacidade e riscos
<!-- PII, prompt injection via documento, limites de upload, isolamento, riscos de custo/latência e mitigação. -->

## 10. Critérios de aceite
<!-- Verificáveis e objetivos. Formato sugerido: "Dado ... quando ... então ...". -->
- [ ] <critério 1>
- [ ] <critério 2>

## 11. Testes esperados
<!-- Marque o que se aplica. -->
- **Unitário:** <o que isolar>
- **Integração:** <contratos/persistência/Milvus>
- **Fluxo:** <jornada ponta a ponta>
- **Avaliação (RAG):** <recall/precisão + grounding, quando envolver retrieval>
- **Regressão:** <o que pode quebrar: contratos, chunking, índice>

## 12. Dependências
<!-- Features, contratos, ADRs ou infraestrutura de que esta feature depende. -->

## 13. Decisões relacionadas (ADRs)
<!-- Links para docs/specs/decisions/. Se esta feature exigir uma decisão nova, registre-a. -->

## 14. Pendências e questões em aberto
<!-- O que ainda precisa ser decidido. Espelhe em status.md → Lacunas conhecidas. -->

## 15. Histórico de atualizações
<!--
A memória da própria spec. Adicione UMA linha por mudança relevante (mais recente no topo).
Mantenha coerente com `version`/`updated` do frontmatter e com o changelog de status.md.
-->
| Data | Versão | Autor | Mudança | Ref (workflow/ADR) |
|---|---|---|---|---|
| <AAAA-MM-DD> | 0.1.0 | <autor> | Criação inicial da spec | — |
