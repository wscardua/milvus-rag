---
description: Fluxo completo de PR — sincroniza o repo, atualiza specs/docs, cria branch/commit, abre a PR, revisa, mergeia e sincroniza a main. Pede autorização uma única vez.
argument-hint: [breve descrição do que está sendo entregue nesta PR] [--auto]
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

> **Se a entrega acima estiver vazia** (nenhuma descrição informada), **monte você a descrição** a partir do que vai subir: analise o diff (`git diff origin/main...HEAD` + arquivos não commitados via `git status`), agrupe por área (skills, specs, ADRs, contratos, infra `ops/`, código `apps/`) e derive daí o **slug do branch**, a **mensagem de commit**, o **título** e o **corpo** da PR. Não peça a descrição ao usuário — infira do conteúdo. `--auto`, se presente, é flag, não descrição.

Use **TodoWrite** para acompanhar. Há **um único ponto de autorização** (passo 3): depois que o usuário autorizar, execute **todos** os passos seguintes — inclusive o **merge** — **sem pedir confirmação de novo**.

## 1. Sincronizar
- `git fetch origin`.
- Se estiver na `main`, `git pull --ff-only`; senão, garanta que a base (`origin/main`) está atualizada.
- Se o working tree tiver arquivos inesperados (lixo, segredos), **pare e avise**.

## 2. Preparar (sem alterar nada ainda)
- Analise o diff e os arquivos a subir; derive a descrição se não foi informada.
- Defina o plano: nome do branch, atualizações de docs/specs previstas (`status.md`, histórico de specs, ADR se aplicável), título/corpo da PR.

## 3. Resumo e AUTORIZAÇÃO (gate único)
Apresente ao usuário um **resumo** contendo:
- o que será entregue (arquivos/áreas), com a descrição informada ou derivada;
- as atualizações de docs/specs que você fará;
- branch, título da PR e que o fluxo irá **até o merge + sync da main**.

Então **peça autorização para prosseguir** e **pare, aguardando a resposta**.
- Se autorizado: siga do passo 4 ao 9 **sem pedir mais nada** (a autorização cobre commit, push, PR, merge e sync).
- Se a entrega contiver `--auto`: pule este gate e prossiga direto.

## 4. Atualizar documentos e specs (metodologia)
Invoque **`milvus-rag-workflow-governor`** e deixe a memória coerente:
- `docs/specs/state/status.md`: linha no **Changelog**, **Status de implementação** e **Trabalho em aberto**.
- Cada feature alterada: **`milvus-rag-spec-editor`** para bump de `version`/`updated` + linha no **Histórico de atualizações**.
- **ADR** novo se mudou fronteira, schema, contrato do índice ou configuração estrutural.
- Confirme que contratos ↔ features ↔ arquitetura ↔ `status.md` não ficaram descasados.

## 5. Branch
- Na `main` (ou default): crie `feature/<slug>` a partir da `main` atualizada — `<slug>` da descrição (informada ou derivada). Já num branch de trabalho: siga nele.

## 6. Commit
- `git add -A`; confira com `git status --short` que **nada sensível** entra (`venv/`, `data/`, `*.env`, `*.log` já estão no `.gitignore`).
- Mensagem clara (o quê + porquê), terminando com:
  `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`

## 7. Push
- `git push -u origin <branch>`.

## 8. Abrir a PR
- `gh pr create --base main --head <branch>` com título e corpo (da descrição informada/derivada), agrupando o que mudou. Finalize o corpo com:
  `🤖 Generated with [Claude Code](https://claude.com/claude-code)`

## 9. Review
- Se houver **código de aplicação** alterado, rode **`/code-review`**; se for só **docs/specs**, revise consistência (contratos ↔ features ↔ `status.md` ↔ ADRs; links/caminhos).
- **Exceção de segurança:** se o review encontrar algo **crítico** (bug grave, segredo, inconsistência séria), **pare e reporte** antes de mergear — mesmo com autorização. Caso contrário, siga direto para o merge.

## 10. Merge (sem nova confirmação)
- A autorização do passo 3 já cobre este passo: `gh pr merge <n> --merge --delete-branch`.
- Verifique com `gh pr view <n>` que `state=MERGED`.

## 11. Sincronizar a main
- `git checkout main && git pull --ff-only`; confirme que `origin/main` e a `main` local batem.

## Ao final, reporte
- Número e URL da PR, estado do merge.
- Resumo do que foi atualizado em `status.md`.
- Pendências registradas (Trabalho em aberto / Lacunas conhecidas).
