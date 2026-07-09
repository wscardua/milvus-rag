# Checklist — FastAPI Domain (RAG)

- a regra de ingestão/retrieval/geração está no backend, e não no Django?
- os schemas de entrada e saída (Pydantic) estão claros?
- os erros previstos estão definidos e consistentes?
- a resposta gerada carrega as citações (chunk + documento de origem)?
- upload valida tipo, tamanho e trata conteúdo como não confiável?
- a mudança impacta o contrato do índice (modelo/dimensão/métrica de embeddings)?
- a alteração exige revisão de testes ou contrato?
