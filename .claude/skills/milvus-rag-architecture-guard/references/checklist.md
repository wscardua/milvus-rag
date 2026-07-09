# Checklist — Fronteiras RAG

- a regra de ingestão/retrieval/geração está no FastAPI, e não no Django?
- o Django permanece cliente (upload, metadados, exibição) sem lógica crítica?
- a persistência (Postgres) está separada da política de produto?
- cada vetor no Milvus referencia um chunk rastreável no Postgres (para citação)?
- modelo de embeddings, dimensão e métrica estão fixados? a mudança foi tratada como ADR + reindexação?
- conteúdo submetido é tratado como entrada não confiável (PII, prompt injection)?
- a mudança exige ADR?
