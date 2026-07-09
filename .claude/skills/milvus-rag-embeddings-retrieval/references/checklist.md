# Checklist — Embeddings & Retrieval

## Índice
- modelo de embeddings, dimensão e métrica estão fixados e documentados?
- a coleção Milvus é consistente (sem misturar modelos/dimensões)?
- cada vetor referencia um chunk rastreável no Postgres?
- há plano de reindexação quando o modelo/dimensão/métrica mudar?

## Ingestão
- extração cobre os tipos de arquivo suportados?
- chunking tem tamanho/overlap definidos e registra posição/origem?
- reprocessar um documento é idempotente (sem duplicar vetores/chunks)?

## Retrieval & geração
- a consulta usa o mesmo modelo de embeddings do índice?
- top-k e filtros por metadado estão definidos?
- a montagem de contexto respeita o limite e deduplica chunks?
- a resposta anexa citações (documento + trecho) dos chunks usados?
- o conteúdo do documento é tratado como não confiável no prompt?

## Avaliação
- existe conjunto fixo de perguntas para medir recall/precisão?
- há checagem de grounding (a resposta cita chunks reais)?
- pergunta, chunks recuperados e citações são auditáveis?
