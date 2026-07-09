---
name: milvus-rag-postgres-modeling
description: Use esta skill para definir ou revisar a modelagem PostgreSQL da POC de RAG — documentos, metadados, chunks, jobs de ingestão e auditoria de consultas — com foco em integridade relacional, rastreabilidade das citações e suporte consistente ao pipeline.
---

# Milvus RAG Postgres Modeling

Use esta skill quando a tarefa principal envolver persistência, esquema relacional ou rastreabilidade de dados.

## Objetivo

Garantir que o banco suporte o pipeline de RAG sem esconder regra de negócio e preservando a trilha que liga cada chunk ao documento de origem.

## Fluxo padrão

1. Verificar trabalho em aberto quando a modelagem alterar contratos, estado ou implementação.
2. Ler a feature alvo em `docs/specs/features/`.
3. Ler `docs/specs/architecture/database.md` e `docs/specs/architecture/vector-index.md`.
4. Ler contratos relevantes (upload/metadados, consulta/citações).
5. Mapear entidades, relacionamentos, constraints e índices.
6. Validar impacto em rastreabilidade das citações, estado de ingestão e performance.
7. Registrar impacto em contratos, testes e estado quando necessário.

## Regras

- O banco persiste a decisão; ele não substitui o domínio (FastAPI).
- Entidades típicas: `document` (arquivo + metadados), `chunk` (texto + posição + referência ao vetor no Milvus), `ingestion_job` (estado/erro), e opcionalmente `query_log` para auditoria.
- Cada `chunk` deve ser rastreável até seu `document` e ao id do vetor no Milvus, para sustentar citações.
- Estado de ingestão (`pending`, `processing`, `indexed`, `failed`) precisa ser historicamente legível para reprocessamento idempotente.
- Índices devem acompanhar os padrões principais de leitura (por documento, por estado de job, por metadado filtrável).
- Alteração de persistência que muda comportamento precisa passar por spec e estado.

## Entradas principais

- `docs/specs/features/`
- `docs/specs/architecture/database.md`
- `docs/specs/architecture/vector-index.md`
- `docs/specs/contracts/`
- `docs/specs/state/status.md`

## Saídas esperadas

- proposta de entidades e relacionamentos
- constraints e índices coerentes
- rastreabilidade chunk → documento → vetor (citações)
- suporte a ingestão idempotente e auditoria
