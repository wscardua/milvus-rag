# Skills — Milvus RAG (POC)

Skills do Claude Code que orientam agentes de IA a trabalhar na POC de RAG: specs, arquitetura, testes, pipeline de RAG e implementação por camada. São leves e ensinam o processo; o conhecimento persistente vive em `docs/specs/`.

Invoque com `/<nome-da-skill>` ou deixe o modelo acioná-las pela `description`.

## Camadas do projeto

- **Django (`apps/web/`)** — UI: upload, metadados, listagem, consulta. Cliente da API.
- **FastAPI (`apps/api/`)** — domínio: ingestão, chunking, embeddings, retrieval, geração com citações.
- **PostgreSQL** — documentos, chunks, metadados, estado de ingestão, auditoria.
- **Milvus** — índice vetorial dos embeddings.

## Skills de governança

| Skill | Quando usar | Saída esperada |
|---|---|---|
| `milvus-rag-workflow-governor` | mudança multi-documento, retomada, bloqueio, conclusão ou reversão | `status.md` atualizado e checklist validado |
| `milvus-rag-spec-editor` | criar, traduzir, normalizar ou alterar specs | specs, contratos, changelog e estado coerentes |
| `milvus-rag-spec-orchestrator` | implementar ou retomar feature a partir das specs | sequência por camada e estado atualizado |
| `milvus-rag-software-architect` | arquitetura, segurança e desenho técnico antes de mudanças relevantes | desenho por camada, riscos, ADRs |
| `milvus-rag-architecture-guard` | validar fronteiras técnicas | alertas de acoplamento e necessidade de ADR |
| `milvus-rag-test-strategy` | definir aceite, cobertura, avaliação de retrieval e regressões | cenários e critérios verificáveis |
| `milvus-rag-test-engineer` | implementar/revisar/executar testes concretos | testes executáveis, evidência e lacunas |

## Skills técnicas

| Skill | Quando usar | Saída esperada |
|---|---|---|
| `milvus-rag-fastapi-domain` | domínio e API em FastAPI (ingestão, retrieval, endpoints) | regras centralizadas, contratos claros, citações |
| `milvus-rag-postgres-modeling` | PostgreSQL (documentos, chunks, jobs, metadados) | modelagem rastreável e auditável |
| `milvus-rag-django-web` | UI Django (upload, metadados, consulta, admin) | telas alinhadas aos contratos, sem regra crítica na UI |
| `milvus-rag-embeddings-retrieval` | núcleo de RAG: chunking, embeddings, Milvus, retrieval, avaliação | pipeline consistente e retrieval avaliável |

## Ordem recomendada

1. `milvus-rag-workflow-governor`
2. `milvus-rag-spec-editor`
3. `milvus-rag-software-architect`
4. `milvus-rag-architecture-guard`
5. `milvus-rag-test-strategy`
6. skill técnica adequada (`fastapi-domain`, `postgres-modeling`, `django-web`, `embeddings-retrieval`)
7. `milvus-rag-test-engineer`
8. `milvus-rag-spec-orchestrator` (condução da implementação)

## Regra central

Conhecimento persistente fica em `docs/specs/`. Skills são leves e ensinam o processo.
