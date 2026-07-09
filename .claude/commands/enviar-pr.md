---
description: Fluxo completo de PR — sincroniza o repo, atualiza specs/docs, cria branch/commit, abre a PR, revisa, mergeia e sincroniza a main.
argument-hint: [breve descrição do que está sendo entregue nesta PR]
allowed-tools: Bash(git:*), Bash(gh:*), Read, Edit, Write, Grep, Glob, TodoWrite, Skill
---

# Enviar PR

Contexto atual (injetado automaticamente):
- Branch: !`git branch --show-current`
- Status: !`git status --short`
- Últimos commits: !`git log --oneline -5`
- Autenticação gh: !`gh auth status 2>&1 | head -3`
- Diff vs origin/main: !`git fetch -q origin 2>/dev/null; git diff --stat origin/main...HEAD 2>/dev/null | tail -25`

**Entrega desta PR:** $ARGUMENTS

> **Se a entrega acima estiver vazia** (nenhuma descrição informada), **monte você a descrição** a partir do que vai subir: analise o diff (`git diff origin/main...HEAD` + arquivos não commitados via `git status`), agrupe as mudanças por área (skills, specs, ADRs, contratos, infra `ops/`, código `apps/`) e derive daí o **slug do branch**, a **mensagem de commit**, o **título** e o **corpo** da PR. Não peça a descrição ao usuário — infira do conteúdo. Só o `--auto` (se presente) é tratado como flag, não como descrição.

Você vai conduzir o fluxo abaixo de ponta a ponta. Use **TodoWrite** para acompanhar os passos. O passo de **merge é irreversível**: pare e peça confirmação explícita antes dele, a menos que a entrega contenha `--auto`.

## 1. Sincronizar
- `git fetch origin`.
- Se estiver na `main`, `git pull --ff-only`; senão, garanta que a base (`origin/main`) está atualizada.
- Se o working tree tiver arquivos inesperados (lixo, segredos), **pare e avise**.

## 2. Atualizar documentos e specs (metodologia)
Invoque a skill **`milvus-rag-workflow-governor`** e deixe a memória coerente com o que está sendo entregue:
- `docs/specs/state/status.md`: adicione linha no **Changelog**, atualize **Status de implementação** e **Trabalho em aberto**.
- Para cada feature alterada: use **`milvus-rag-spec-editor`** para dar bump em `version`/`updated` e adicionar linha no **Histórico de atualizações** da spec.
- Registre um **ADR** novo se a entrega mudou fronteira, schema, contrato do índice ou configuração estrutural.
- Confirme que contratos ↔ features ↔ arquitetura ↔ `status.md` não ficaram descasados.

## 3. Branch
- Se estiver na `main` (ou branch default), crie um branch descritivo a partir da `main` atualizada: `feature/<slug>` — o `<slug>` vem da descrição (informada ou derivada do diff).
- Se já estiver num branch de trabalho, siga nele.

## 4. Commit
- `git add -A`; confira com `git status --short` que **nada sensível** entra (`venv/`, `data/`, `*.env`, `*.log` já estão no `.gitignore` — valide de novo).
- Commit com mensagem clara (o quê + porquê), terminando com:
  `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`

## 5. Push
- `git push -u origin <branch>`.

## 6. Abrir a PR
- `gh pr create --base main --head <branch>` com título objetivo e corpo (baseados na descrição informada ou derivada) resumindo o que mudou, agrupado por área (skills / specs / ADRs / contratos / infra / código). Finalize o corpo com:
  `🤖 Generated with [Claude Code](https://claude.com/claude-code)`
- Guarde o número e a URL da PR.

## 7. Review
- Revise o diff da PR:
  - Se houver **código de aplicação** alterado, rode a skill **`/code-review`**.
  - Se for só **docs/specs**, faça uma revisão de consistência (contratos ↔ features ↔ `status.md` ↔ ADRs; links e caminhos válidos).
- Reporte os achados de forma resumida. Se houver algo **crítico**, pare e pergunte antes de mergear.

## 8. Merge (confirmar antes)
- Só após o review e a **confirmação do usuário** (ou se a entrega tiver `--auto`): `gh pr merge <n> --merge --delete-branch`.
- Verifique com `gh pr view <n>` que `state=MERGED`.

## 9. Sincronizar a main
- `git checkout main && git pull --ff-only`.
- Confirme que `origin/main` e a `main` local apontam para o mesmo commit.

## Ao final, reporte
- Número e URL da PR, estado do merge.
- Resumo do que foi atualizado em `status.md`.
- Qualquer pendência registrada (Trabalho em aberto / Lacunas conhecidas).
