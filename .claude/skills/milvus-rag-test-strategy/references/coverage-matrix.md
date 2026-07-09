# Matriz mínima — RAG

- unitário: regra isolada (chunking, montagem de prompt, parsing de metadados)
- integração: contrato Django↔FastAPI, persistência Postgres, indexação/busca no Milvus
- fluxo: jornada principal (upload → ingestão → indexação → consulta → resposta com citações)
- avaliação: recall/precisão de retrieval sobre um conjunto fixo de perguntas; respostas citam chunks reais
- regressão: contratos, estratégia de chunking, modelo/dimensão de embeddings e métrica do índice
