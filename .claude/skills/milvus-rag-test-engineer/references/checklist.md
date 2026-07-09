# Checklist — Testes RAG

- quais critérios de aceite precisam virar teste?
- há testes de domínio/API (FastAPI)?
- há testes de persistência (Postgres: documentos, chunks, estado)?
- há testes de indexação e busca no Milvus?
- a ingestão testa extração, chunking e idempotência de reprocessamento?
- há avaliação de retrieval (recall/precisão) e checagem de grounding das citações?
- há testes de upload/metadados/renderização no Django?
- regressões por contrato foram cobertas?
- execução foi registrada em `status.md`?
