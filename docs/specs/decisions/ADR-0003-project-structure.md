# ADR-0003 — Estrutura de diretórios do projeto

## Contexto

As specs tratam `apps/web/`, `apps/api/` e `ops/` como estrutura-alvo, mas o layout interno não estava fixado. É preciso definir a organização do monorepo antes de materializar o código, respeitando o guardrail Django=cliente / FastAPI=domínio.

## Decisão

Monorepo com um `venv/` compartilhado (Python 3.10) na raiz:

```
milvus-rag/
├── ops/                      # infra local (Podman): postgres + milvus + etcd + minio
├── apps/
│   ├── api/                  # FastAPI — DOMÍNIO (fonte da verdade)
│   │   ├── app/
│   │   │   ├── main.py · config.py
│   │   │   ├── worker.py     # daemon de ingestão (consome ingestion_job) — ADR-0004
│   │   │   ├── api/          # routers finos (HTTP)
│   │   │   ├── schemas/      # Pydantic = contratos
│   │   │   ├── domain/       # ingestion/ + retrieval/ (regras)
│   │   │   ├── services/     # embeddings.py · llm.py · vectorstore.py (integrações)
│   │   │   └── db/           # SQLAlchemy models + sessão
│   │   ├── migrations/       # Alembic
│   │   ├── tests/ · eval/
│   │   ├── requirements.txt · .env.example
│   ├── web/                  # Django — APRESENTAÇÃO (cliente da API)
│   │   ├── manage.py · config/
│   │   ├── documents/        # upload + metadados + listagem
│   │   ├── query/            # consulta + citações
│   │   ├── templates/ · static/
│   │   ├── requirements.txt · .env.example
│   └── mcp/                  # servidor MCP (cliente HTTP da API) — ADR-0005
│       ├── server.py · tools/
│       ├── requirements.txt · .env.example
├── docs/ · .claude/skills/
└── data/                     # dados locais persistentes (gitignored)
    ├── uploads/              # arquivos enviados (app)
    └── volumes/              # dados dos containers (postgres/milvus/etcd/minio) — DATA_DIR
```

Decisões-chave:
- **`domain/` separado de `services/`** no FastAPI: regra central isolada das integrações (LM Studio/Milvus), testável sem infra.
- **`schemas/` (Pydantic)** materializa os contratos `upload-and-metadata` e `query-and-citations`.
- **Migrations com Alembic + SQLAlchemy** no FastAPI (schema é do domínio, não da UI Django).
- **`data/uploads/` na raiz**: dado de aplicação (arquivos originais), persistente e fora do git.
- **Dois `requirements.txt`** (api e web) no mesmo `venv`.

## Impacto

- `spec-orchestrator` passa a implementar seguindo este layout.
- Backend não depende de `sentence-transformers`; embeddings via LM Studio (ADR-0002).
- `ops/` já criado com `docker-compose.yml` (volumes nomeados persistentes).
- Worker de ingestão vive em `apps/api/app/worker.py` (ADR-0004); servidor MCP em `apps/mcp/` (ADR-0005), ambos reusando o domínio/contratos da API.

## Alternativas rejeitadas

- **Schema derivado dos models do Django**: acoplaria domínio à apresentação — contra o guardrail.
- **Estrutura flat no FastAPI (sem domain/services)**: espalharia regra crítica.
- **`data/` dentro de `ops/volumes/`**: mistura dado de aplicação com volume de container.

## Data

2026-07-09

## Status

aceita
