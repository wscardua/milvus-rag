# Checklist — Arquitetura RAG

- a mudança exige nova fronteira ou ADR?
- existem riscos de autenticação, autorização, isolamento por usuário/tenant ou dados sensíveis nos documentos?
- há mitigação para prompt injection vindo do conteúdo submetido?
- o desenho mantém Django como apresentação/cliente (upload + metadados) e FastAPI como domínio?
- todo chunk retornado é rastreável até o documento de origem (citações)?
- modelo de embeddings, dimensão e métrica de similaridade estão fixados e versionados? mudança implica reindexação planejada?
- a estratégia de chunking e o versionamento/reindexação de documentos estão definidos?
- o PostgreSQL persiste metadados, estado de ingestão e histórico suficientes para auditoria?
- jobs de ingestão são idempotentes e reprocessáveis?
- custo/latência de embeddings e de retrieval foram considerados para a escala da POC?
- há testes arquiteturais, de integração (FastAPI ↔ Milvus/Postgres) ou de segurança esperados?
