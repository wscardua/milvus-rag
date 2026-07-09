---
name: milvus-rag-django-web
description: Use esta skill para implementar a camada web da POC de RAG com Django — upload de arquivos, formulários de metadados, listagem de documentos, tela de consulta e admin — respeitando os contratos da API FastAPI e sem mover regra crítica para a UI.
---

# Milvus RAG Django Web

Use esta skill quando a tarefa principal estiver na camada de apresentação e operação web em Django.

## Objetivo

Implementar as telas de **carga de arquivos e definição de metadados**, listagem/estado dos documentos, consulta ao RAG e exibição de respostas com citações, sem colocar lógica de ingestão/retrieval na UI.

Django vive em `apps/web/`: apps em `apps/web/django/`, templates em `apps/web/templates/`, assets em `apps/web/static/` (ajuste conforme a estrutura real ao criá-la). Preserve `AppConfig.label` e migrations estáveis quando houver.

## Fluxo padrão

1. Verificar trabalho em aberto quando houver mudança multi-documento.
2. Ler a feature alvo em `docs/specs/features/`.
3. Ler `docs/specs/architecture/frontend-web.md`.
4. Ler os contratos listados no frontmatter da feature (upload/metadados, consulta/citações).
5. Revisar `docs/specs/testing/` para critérios de aceite e fluxos esperados.
6. Implementar templates, views, formulários de upload/metadados e a tela de consulta.
7. Registrar testes executados ou pendentes em `status.md`.

## Regras

- A UI representa o estado do domínio; ela não faz chunking, embeddings nem retrieval.
- Upload e consulta devem passar pelos contratos da API FastAPI.
- Valide no formulário o tipo/tamanho do arquivo e os metadados obrigatórios antes de enviar.
- Exiba estado de ingestão do documento (`pending`, `processing`, `indexed`, `failed`) de forma clara.
- Ao mostrar respostas do RAG, apresente as citações (documento/trecho de origem) retornadas pela API.
- O admin Django é suporte e operação, não atalho para burlar regras do domínio.
- Mudança visual que altera comportamento deve voltar para a spec antes de fechar.

## Entradas principais

- `docs/specs/features/`
- `docs/specs/architecture/frontend-web.md`
- `docs/specs/contracts/`
- `docs/specs/testing/`

## Saídas esperadas

- telas de upload, metadados, listagem e consulta coerentes com a spec
- validação de arquivo e metadados no cliente/servidor
- exibição de estado de ingestão e de citações
- aderência às fronteiras entre UI e domínio
