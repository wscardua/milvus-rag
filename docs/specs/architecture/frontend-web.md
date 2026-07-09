# Arquitetura — Frontend Web (Django)

Camada web em `apps/web/`. Cliente da API FastAPI.

## Responsabilidades

- Tela de **upload** com formulário de **metadados**.
- Listagem de documentos com **estado de ingestão** (`pending`, `processing`, `indexed`, `failed`).
- Tela de **consulta** e exibição da resposta com **citações**.
- Admin para operação/suporte.

## Regras

- Não faz chunking, embeddings nem retrieval — tudo via API.
- Valida tipo/tamanho de arquivo e metadados obrigatórios.
- Exibe as citações retornadas pela API sem recalcular nada.
- Admin não burla validações do domínio.
