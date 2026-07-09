---
description: Inicia uma nova feature/atualização/correção — cria branch a partir da main remota e prepara specs e memória (status.md, feature a partir do template). Pede autorização uma única vez.
argument-hint: [feat|fix|update] <descrição da feature/mudança> [--auto]
allowed-tools: Bash(git:*), Read, Edit, Write, Grep, Glob, TodoWrite, Skill
---

# Iniciar Feature

Contexto atual (injetado automaticamente):
- Branch: !`git branch --show-current`
- Status (working tree): !`git status --short`
- main remota: !`git fetch -q origin 2>/dev/null; git log --oneline -1 origin/main 2>/dev/null`
- Últimas features: !`ls docs/specs/features/ 2>/dev/null | grep -v _TEMPLATE`

**Pedido:** $ARGUMENTS

> Interprete o **tipo** (feature | atualização | correção) e um **slug** curto a partir do pedido. Se o pedido vier com prefixo `feat`/`fix`/`update`, use-o; senão, infira. `--auto`, se presente, é flag (pula o gate), não faz parte da descrição. Não peça a descrição de volta — infira do pedido.

Use **TodoWrite** para acompanhar. Há **um único ponto de autorização** (passo 3): após o OK, execute todos os passos seguintes sem pedir de novo.

## 1. Pré-checagem
- Se o **working tree estiver sujo** (mudanças não commitadas), **pare e avise** — iniciar uma feature nova deve partir de um estado limpo. Sugira commitar/`stash` antes. Não descarte nada por conta própria.
- `git fetch origin` para trazer a `main` remota.

## 2. Preparar (sem alterar nada ainda)
- Defina: **tipo** (`feature`/`fix`/`update`), **slug** e **nome do branch** (`feature/<slug>`, `fix/<slug>` ou `update/<slug>`).
- Decida o impacto documental:
  - **Feature nova** → criará uma spec em `docs/specs/features/<slug>.md` a partir de `docs/specs/features/_TEMPLATE.md`.
  - **Atualização/correção de feature existente** → identificará a(s) spec(s) afetada(s); os ajustes de conteúdo e o bump de versão acontecem durante o trabalho (e no `/enviar-pr`).
- Escolha o próximo `WORK-<n>` (sequencial, olhando `docs/specs/state/status.md`).

## 3. Resumo e AUTORIZAÇÃO (gate único)
Apresente um **resumo**: tipo, nome do branch, spec que será criada (se houver), e a entrada `WORK-<n>` que abrirá no `status.md`. Então **peça autorização e pare, aguardando**.
- Autorizado → siga do passo 4 ao 6 sem pedir mais nada.
- `--auto` → pule o gate.

## 4. Criar o branch a partir da main remota
- `git checkout -b <branch> origin/main` (garante base na `main` remota atualizada, independente do branch atual).

## 5. Preparar specs e memória
Invoque **`milvus-rag-workflow-governor`** e **`milvus-rag-spec-editor`**:
- `docs/specs/state/status.md`:
  - **Trabalho em aberto**: adicione a linha `WORK-<n>` (feature alvo, etapa = "iniciada", próxima ação, status `aberto`).
  - **Changelog**: uma linha registrando o início do trabalho.
- **Feature nova**: copie `docs/specs/features/_TEMPLATE.md` para `docs/specs/features/<slug>.md`, preencha o que já se sabe do pedido (visão, escopo, contratos prováveis, ADRs relacionados), com `status_spec: rascunho`, `status_impl: nao_iniciada`, `version: 0.1.0` e a 1ª linha do **Histórico de atualizações**; adicione a feature à tabela **Status de implementação**.
- **Atualização/correção**: registre no `WORK-<n>` a(s) spec(s) afetada(s); não altere ainda o conteúdo delas (isso é parte do trabalho).
- Confirme que nada ficou descasado.

## 6. Reportar
- Branch criado (e a partir de qual commit da `main`).
- Specs/memória criadas ou atualizadas.
- Próximos passos: implementar; ao concluir, rodar **`/enviar-pr`** para revisar e mergear.

> Este command **não** commita nem faz push — apenas prepara o branch e a base documental. O envio é responsabilidade do `/enviar-pr`.
