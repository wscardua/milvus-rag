# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## O que é este repositório

POC de **RAG sobre documentos submetidos**: upload de arquivos com metadados, ingestão (chunking + embeddings), indexação no **Milvus**, e consulta em linguagem natural com **respostas sempre citando a origem** (grounding).

Estado atual: **docs-first**. Só existem specs (`docs/specs/`) e skills (`.claude/skills/`) — o código de aplicação (`apps/web/`, `apps/api/`, `ops/`) ainda **não foi criado**. Por isso ainda não há comandos de build/lint/test; ao criar código, documente-os aqui.

## Ambiente de desenvolvimento

- **Virtualenv:** `venv/` na raiz (**Python 3.10**), compartilhado pelo código Python (FastAPI + Django). Ative com `source venv/bin/activate`. Está no `.gitignore` — não commitar.
- **Containers:** Postgres + Milvus via `compose` em `ops/`, runtime **Podman** (`podman compose`). Dados persistem em **bind mounts no projeto** (`data/volumes/`, via `DATA_DIR`), separados de `data/uploads/` (arquivos de app). Tudo gitignored.
- **Configuração (ADR-0006):** nada hardcoded — endpoints, credenciais e modelos vêm de env, com config única por app (`app/config.py` no FastAPI). Migrar para serviços gerenciados (Postgres gerenciado, Zilliz Cloud, LLM/embeddings na nuvem) é troca de `.env`.
- **Inferência local:** LM Studio precisa estar ativo com **dois modelos carregados** — embedding (`embeddinggemma-300m`) e um de chat.
- Ao criar dependências, versione um `requirements.txt` (ou `pyproject.toml`) em `apps/api/` e `apps/web/`.
- Estrutura de diretórios: ver [ADR-0003](docs/specs/decisions/ADR-0003-project-structure.md).

## Comandos

```bash
# Infra (Postgres + Milvus + etcd + minio) — em ops/
cd ops && cp .env.example .env      # 1ª vez
podman compose up -d                # subir (dados persistem em volumes nomeados)
podman compose ps                   # status + health
podman compose down                 # parar SEM apagar dados (nunca use -v salvo p/ resetar)
```

Milvus: `localhost:19530` (gRPC) · Postgres: `postgresql://rag:rag@localhost:5432/rag`. Detalhes e backup de volumes em [ops/README.md](ops/README.md).

```bash
# Backend (apps/api) — venv/ compartilhado na raiz; rodar de dentro de apps/api
source venv/bin/activate && pip install -r apps/api/requirements.txt   # 1ª vez
cd apps/api && cp -n .env.example .env                                 # 1ª vez
alembic upgrade head                        # aplica migrations no Postgres
alembic revision --autogenerate -m "msg"    # nova migration a partir dos models
python -m app.db.seed_taxonomy              # seed idempotente da taxonomia (ADR-0007)
uvicorn app.main:app --port 8001            # sobe a API (domínio: /documents, /query, org, links)
python -m app.worker                        # sobe o worker de ingestão (ADR-0004/0009) — precisa do LM Studio
```

LM Studio deve estar ativo em `LM_STUDIO_BASE_URL` com **embedding** (`text-embedding-embeddinggemma-300m`) e **chat** (ex.: `gemma-3-4b-it-qat`) — modelos carregam sob demanda (JIT).

```bash
# Frontend (apps/web) — Django, cliente HTTP da API (venv/ compartilhado)
source venv/bin/activate && pip install -r apps/web/requirements.txt   # 1ª vez
cd apps/web && cp -n .env.example .env                                 # 1ª vez (API_BASE_URL)
python manage.py runserver 127.0.0.1:8000    # sobe a UI (API precisa estar em :8001)
```

Rodar os três juntos: API `uvicorn app.main:app --port 8001` (em `apps/api`), UI `manage.py runserver` (em `apps/web`), e — quando existir — o worker `python -m app.worker`.

```bash
# Servidor MCP (apps/mcp) — cliente HTTP da API (ADR-0005); venv/ compartilhado
source venv/bin/activate && pip install -r apps/mcp/requirements.txt   # 1ª vez (fixa mcp/starlette compatíveis com o FastAPI)
cd apps/mcp && cp -n .env.example .env                                 # 1ª vez (API_BASE_URL=http://localhost:8001)
python -m app.server                                                   # sobe o MCP (stdio): search_documents/retrieve_chunks/list_documents/get_document
```

O MCP consome a API (`POST /query`, `POST /retrieve`, `GET /documents[...]`) — a API precisa estar em `:8001`. Transporte `stdio` por default (`MCP_TRANSPORT`).

```bash
# Testes (apps/api) — integração via FastAPI TestClient contra o stack real (Postgres/Milvus/LM Studio)
source venv/bin/activate && cd apps/api && pytest   # precisa da infra up + org/taxonomia seedada; testes de /query pulam se o LM Studio estiver fora
```

## Metodologia: docs como fonte da verdade

O desenvolvimento é **guiado por specs**, não pelo histórico da conversa. Antes de implementar, leia `docs/specs/` e conduza pelas skills `milvus-rag-*`.

- **Fonte da verdade documental:** `docs/specs/`. Nunca implemente comportamento que não esteja na spec — se precisar de regra nova, ajuste a spec primeiro (skill `milvus-rag-spec-editor`).
- **Memória operacional única:** [docs/specs/state/status.md](docs/specs/state/status.md) — trabalho em aberto, status de implementação, changelog global e lacunas conhecidas. É o ponto de retomada de qualquer sessão; mantenha-o atualizado.
- **Toda feature parte de** [docs/specs/features/_TEMPLATE.md](docs/specs/features/_TEMPLATE.md); **todo ADR parte de** [docs/specs/decisions/_TEMPLATE-ADR.md](docs/specs/decisions/_TEMPLATE-ADR.md).
- **Versionamento de spec:** a cada mudança relevante numa feature, incremente `version`, atualize `updated`, adicione uma linha na seção **15. Histórico de atualizações** da própria spec (nunca apague linhas) e registre o mesmo evento no changelog de `status.md`.
- A persistência dessa memória é **por convenção** (as skills instruem; nada roda automático). Ao terminar uma mudança multi-documento, atualize `status.md` explicitamente.

## Arquitetura por camadas (guardrails)

Ver [docs/specs/architecture/system-overview.md](docs/specs/architecture/system-overview.md). A separação de responsabilidades é regra dura — validável pela skill `milvus-rag-architecture-guard`:

| Camada | Local | Responsabilidade |
|---|---|---|
| Web (Django) | `apps/web/` | Upload, metadados, listagem, consulta, admin. **Cliente da API — não faz chunking/embeddings/retrieval.** |
| MCP (servidor) | `apps/mcp/` | Consulta ao acervo para outros agentes. **Cliente HTTP da API** (ADR-0005). |
| API/Domínio (FastAPI) | `apps/api/` | **Fonte da verdade:** retrieval e geração com citações; enfileira ingestão. |
| Worker (ingestão) | `apps/api/app/worker.py` | Daemon assíncrono que consome `ingestion_job` e roda o pipeline (ADR-0004). |
| Banco (PostgreSQL) | container | `document`, `chunk`, `ingestion_job`, `query_log?`. Persiste, não decide política. |
| Índice (Milvus) | container | Busca por similaridade. |

**Stack decidida (ADR-0002), tudo local:** embeddings **e** geração servidos pelo **LM Studio** (API OpenAI-compatível, `base_url` por env) — embeddings `embeddinggemma-300m` (768, COSINE) em `/v1/embeddings`, chat em `/v1/chat/completions`; o backend é cliente leve (sem ML no processo). **Postgres + Milvus** sobem juntos em containers via `compose` em `ops/` (runtime **Podman**). Formatos aceitos: PDF, DOCX, TXT/MD, HTML, `.py`, XLS/XLSX. Nenhum conteúdo sai do ambiente.

Invariantes centrais:
- **Grounding obrigatório:** toda resposta gerada carrega citações (chunk + documento de origem).
- **Rastreabilidade:** cada vetor no Milvus referencia um `chunk` rastreável no Postgres.
- **Contrato do índice:** modelo de embeddings, dimensão e métrica de similaridade são imutáveis por coleção — mudá-los exige **ADR + reindexação** (nunca misture vetores de modelos diferentes).
- **Ingestão assíncrona e idempotente:** o upload só enfileira (`ingestion_job=pending`); o worker processa (ADR-0004). Reprocessar um documento não duplica chunks nem vetores.
- **Consulta por dois canais:** UI Django e servidor MCP (ADR-0005) — ambos clientes da API, nunca acessam Milvus/Postgres direto.
- **Entrada não confiável:** conteúdo submetido pode conter PII e tentativas de prompt injection; trate-o como não confiável ao montar prompts.

## Skills (`.claude/skills/`)

Skills leves que ensinam o processo; índice em [.claude/skills/README.md](.claude/skills/README.md). Invoque com `/<nome>` ou deixe o modelo acioná-las pela `description`.

- **Governança:** `milvus-rag-workflow-governor` (coordena mudança multi-documento via `status.md`), `milvus-rag-spec-editor` (dona da regra de template + versionamento), `milvus-rag-spec-orchestrator` (conduz implementação a partir das specs), `milvus-rag-software-architect`, `milvus-rag-architecture-guard`, `milvus-rag-test-strategy`, `milvus-rag-test-engineer`.
- **Stack:** `milvus-rag-fastapi-domain`, `milvus-rag-postgres-modeling`, `milvus-rag-django-web`, `milvus-rag-embeddings-retrieval` (núcleo de RAG: chunking, embeddings, Milvus, retrieval, avaliação).

Ordem recomendada de trabalho: workflow-governor → spec-editor → software-architect → architecture-guard → test-strategy → skill técnica adequada → test-engineer → spec-orchestrator.

## Gatilhos de ADR

Registre uma decisão (`docs/specs/decisions/`) quando mudar: fronteira entre camadas; modelo/dimensão/métrica de embeddings (implica reindexação); schema estrutural (`document`/`chunk`/`ingestion_job`); estratégia de chunking que afete retrieval.

## Testes e avaliação

Estratégia em [docs/specs/testing/test-strategy.md](docs/specs/testing/test-strategy.md). Além de unit/integração/fluxo, RAG exige **avaliação de retrieval** (recall/precisão sobre um conjunto fixo de perguntas) e **checagem de grounding** (a resposta cita chunks reais). Uma feature só vira `validada` com evidência de teste ou pendência justificada em `status.md`.
