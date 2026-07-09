# Checklist — Postgres Modeling (RAG)

- `document`, `chunk` e `ingestion_job` estão modelados com integridade?
- cada `chunk` referencia seu `document` e o id do vetor correspondente no Milvus?
- o estado de ingestão permite reprocessamento idempotente?
- metadados filtráveis (autor, tipo, tags, data) estão persistidos e indexados?
- faltam constraints de integridade (FK, unique, not null)?
- os índices cobrem leituras por documento, por estado e por metadado?
- a modelagem preserva rastreabilidade para citações e auditoria?
