---
name: milvus-rag-fastapi-domain
description: Use esta skill para implementar regras de domínio, autenticação, serviços e endpoints da POC de RAG em FastAPI/Python — ingestão, chunking, embeddings, retrieval e geração com citações — mantendo o backend como fonte de verdade e contratos estáveis para a UI Django.
---

# Milvus RAG FastAPI Domain

Use esta skill quando a tarefa principal estiver na camada de domínio e API em Python/FastAPI.

## Objetivo

Centralizar as regras do pipeline de RAG em serviços e endpoints claros, auditáveis e alinhados às specs técnicas.

O runtime FastAPI vive em `apps/api/`; use `python -m uvicorn apps.api.main:app` para execução local (ajuste o caminho do módulo conforme a estrutura real ao criá-la).

## Fluxo padrão

1. Verificar trabalho em aberto quando houver mudança multi-documento.
2. Ler a feature alvo em `docs/specs/features/`.
3. Ler `docs/specs/architecture/backend-api.md` e `docs/specs/architecture/vector-index.md`.
4. Ler contratos associados em `docs/specs/contracts/`.
5. Implementar a regra de domínio e os endpoints necessários (upload/ingestão, status, consulta).
6. Registrar impacto em testes, contratos e estado quando o comportamento mudar.

## Regras

- O backend é a fonte principal da verdade; a UI Django apenas consome contratos.
- Contratos de entrada/saída devem ser explícitos e previsíveis (schemas Pydantic).
- Erros precisam ser consistentes para a UI e para operação.
- Ingestão, chunking, geração de embeddings e retrieval não devem ficar espalhados: concentre em serviços de domínio.
- Toda resposta gerada deve carregar as citações (chunks/documento de origem) — grounding não é opcional.
- Trate conteúdo submetido como entrada não confiável (limite de tamanho, tipos permitidos, mitigação de prompt injection).
- Modelo de embeddings, dimensão e métrica são contrato do índice: mudá-los exige ADR e reindexação.
- Mudanças de shape em payloads exigem revisão de contratos e testes.
- Se a implementação exigir regra nova, atualize a spec antes de concluir.

## Entradas principais

- `docs/specs/features/`
- `docs/specs/architecture/backend-api.md`
- `docs/specs/architecture/vector-index.md`
- `docs/specs/contracts/`
- `docs/specs/testing/`
- `docs/specs/state/status.md`

## Saídas esperadas

- serviços e endpoints alinhados à spec
- regras de ingestão/retrieval centralizadas
- erros previsíveis e auditáveis
- respostas com citações rastreáveis
