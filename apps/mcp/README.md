# Servidor MCP — consulta ao acervo (FEAT-MCP-001)

Canal de consulta ao acervo para **outros agentes**, via Model Context Protocol.
É um **cliente HTTP da API FastAPI** (ADR-0005): não fala com Milvus/Postgres nem
reimplementa retrieval — cada tool vira uma chamada à API, que continua a fonte da
verdade (retrieval, geração e citações vêm prontos de lá).

## Pré-condições

- API FastAPI no ar em `API_BASE_URL` (default `http://localhost:8001`) com documentos
  indexados (ver [apps/api](../api)). O LM Studio precisa estar ativo para as tools que
  geram/embedam (`search_documents`, `retrieve_chunks`).

## Instalar e rodar (stdio)

```bash
source ../../venv/bin/activate && pip install -r requirements.txt   # 1ª vez (venv/ na raiz)
cp -n .env.example .env                                             # 1ª vez (API_BASE_URL)
python -m app.server                                                # sobe o servidor MCP (stdio)
```

`stdio` é o transporte default (integração local com agentes). Para expor por rede,
ajuste `MCP_TRANSPORT` no `.env` (evolução futura — a POC é local, sem auth).

## Tools

### Consulta

| Tool | Chamada na API | Retorno |
|---|---|---|
| `search_documents(question, filters?, top_k?)` | `POST /query` | resposta gerada + `citations` + `linked_flow` |
| `retrieve_chunks(question, filters?, top_k?)` | `POST /retrieve` | apenas trechos (`chunks` + `score`), sem geração |
| `list_documents(filters?)` | `GET /documents` | acervo por categoria/metadado |
| `get_document(id)` | `GET /documents/{id}` | metadados + estado de ingestão |

`filters` (dict, opcional) aceita:
- `squad`, `delivery_process`, `category` — **UUID**, não o nome. Resolva com as tools de lookup abaixo antes de filtrar.
- `doc_type`, `delivery_phase` — string, lista fechada (`list_doc_types`/`list_delivery_phases`).
- `tags` (ADR-0015) — lista de strings, semântica **OR**: documento com qualquer uma das tags pedidas entra no resultado (não precisa ter todas). Veja os valores existentes com `list_tags`.
- `list_documents` também aceita `limit`/`offset`.

### Lookup (WORK-010)

Para o agente resolver **nome→id** (ou ver os valores válidos de um campo fechado) antes de montar `filters` nas tools acima — sem isso, não há como filtrar por `squad`/`delivery_process` (a API exige UUID, não o nome):

| Tool | Chamada na API | Retorno |
|---|---|---|
| `list_squads()` | `GET /squads` | squads cadastradas |
| `list_delivery_processes(squad_id?)` | `GET /delivery-processes` | processos de delivery, filtrável por squad |
| `list_categories()` | `GET /categories` | categorias da taxonomia |
| `list_doc_types()` | `GET /doc-types` | lista fechada de `doc_type` |
| `list_delivery_phases()` | `GET /delivery-phases` | lista fechada de fases de delivery |
| `list_tags()` | `GET /tags` | tags distintas já usadas no acervo |

Com a API fora do ar, as tools retornam **erro explícito** ao agente (não inventam resposta).

## Conectar de um cliente MCP

Exemplo de configuração (cliente que spawna o processo via stdio):

```json
{
  "mcpServers": {
    "milvus-rag": {
      "command": "python",
      "args": ["-m", "app.server"],
      "cwd": "/caminho/para/milvus-rag/apps/mcp",
      "env": { "API_BASE_URL": "http://localhost:8001" }
    }
  }
}
```
