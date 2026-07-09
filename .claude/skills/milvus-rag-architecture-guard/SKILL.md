---
name: milvus-rag-architecture-guard
description: Use esta skill para validar fronteiras arquiteturais da POC de RAG, impedir mistura de responsabilidades entre Django (UI), FastAPI (domínio), PostgreSQL (metadados) e Milvus (índice vetorial), e revisar impactos estruturais de novas features ou mudanças de spec.
---

# Milvus RAG Architecture Guard

Use esta skill quando a tarefa exigir decidir onde uma responsabilidade deve viver ou verificar se uma proposta respeita a arquitetura.

## Objetivo

Proteger a separação entre camada web (Django), domínio (FastAPI), persistência de metadados (PostgreSQL) e índice vetorial (Milvus).

## Fluxo padrão

1. Verificar se a mudança tem entrada em `docs/specs/state/status.md`.
2. Ler a feature alvo.
3. Ler os contratos associados.
4. Revisar os docs de arquitetura relevantes.
5. Mapear responsabilidades por camada.
6. Sinalizar violações, orientar correção e indicar necessidade de ADR.

## Regras

- `frontend-web` (Django) não calcula regra crítica de RAG: faz upload, coleta metadados, exibe resultados e consome a API.
- `backend-api` (FastAPI) é a fonte da verdade: ingestão, chunking, embeddings, retrieval e geração com citações.
- `database` (PostgreSQL) persiste documentos, chunks, metadados e estado; não decide política de produto sozinho.
- `vector-index` (Milvus) guarda embeddings e serve busca por similaridade; cada vetor deve referenciar um chunk rastreável no Postgres.
- Modelo de embeddings, dimensão e métrica de similaridade são contrato do índice: mudança exige ADR e reindexação planejada.
- Django em `apps/web/`, FastAPI em `apps/api/`, deploy/scripts/Docker em `ops/`.
- Mudanças de fronteira devem atualizar estado e decisões.

## Entradas principais

- `docs/specs/architecture/`
- `docs/specs/features/`
- `docs/specs/contracts/`
- `docs/specs/decisions/`
- `docs/specs/state/status.md`

## Saídas esperadas

- validação de fronteiras
- alertas de acoplamento
- necessidade de ADR quando houver mudança estrutural
