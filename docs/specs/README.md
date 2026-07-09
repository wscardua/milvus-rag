# Specs — Milvus RAG (POC)

Fonte da verdade documental da POC de RAG. Metodologia enxuta: specs curtas + critérios de aceite + um único arquivo de estado.

## Estrutura

- `product/overview.md` — visão funcional do RAG (o que a POC faz e para quem).
- `features/` — uma spec por feature. **Toda feature nova parte de `features/_TEMPLATE.md`.**
- `contracts/` — contratos entre Django (UI) e FastAPI (API).
- `architecture/` — desenho por camada (sistema, backend, frontend, banco, índice vetorial).
- `testing/` — estratégia de testes e critérios de aceite.
- `decisions/` — ADRs (decisões estruturais). **Todo ADR novo parte de `decisions/_TEMPLATE-ADR.md`.**
- `state/status.md` — memória operacional única: trabalho em aberto, status de implementação, changelog e lacunas.

## Templates

- `features/_TEMPLATE.md` — spec de feature completa e preenchível, com **Histórico de atualizações** próprio (versão, data, autor, mudança). Dá a visão para entender a spec e sua evolução, e guia o desenvolvimento.
- `decisions/_TEMPLATE-ADR.md` — decisão arquitetural (contexto, decisão, impacto, alternativas, status).

Regra de versionamento: a cada mudança relevante numa spec, incremente `version`, atualize `updated`, adicione uma linha no **Histórico de atualizações** da spec e registre o mesmo evento no changelog de `state/status.md`. O histórico nunca é apagado — só recebe novas linhas. A skill `milvus-rag-spec-editor` é responsável por aplicar essa regra.

## Regra central

Conhecimento persistente fica aqui. As skills em `.claude/skills/` são leves e ensinam o processo.

## Camadas

- **Django (`apps/web/`)** — UI: upload de arquivos, metadados, listagem, consulta. Cliente da API.
- **FastAPI (`apps/api/`)** — domínio: ingestão, chunking, embeddings, retrieval, geração com citações.
- **PostgreSQL** — documentos, chunks, metadados, estado de ingestão, auditoria.
- **Milvus** — índice vetorial dos embeddings.
