# Estratégia de Testes — Milvus RAG (POC)

## Níveis

- **Unitário**: chunking, validação de metadados, montagem de prompt/contexto.
- **Integração**: contratos Django↔FastAPI, persistência Postgres, indexação/busca no Milvus.
- **Fluxo**: upload → ingestão → indexação → consulta → resposta com citações.
- **Avaliação de RAG**: recall/precisão de retrieval sobre conjunto fixo de perguntas; grounding das citações.
- **Regressão**: contratos, chunking, modelo/dimensão/métrica de embeddings.

## Regras

- Feature só vira `validada` com evidência de teste ou pendência justificada.
- Mudança no contrato do índice exige reavaliação de retrieval.
- Pendências ficam registradas em `docs/specs/state/status.md` (Lacunas conhecidas).
