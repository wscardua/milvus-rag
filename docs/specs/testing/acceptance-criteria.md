# Critérios de Aceite — POC

## Upload (FEAT-UPLOAD-001)
- upload válido cria documento e inicia ingestão
- tipo/tamanho inválido é rejeitado com mensagem clara
- estado de ingestão visível e atualizado

## Ingestão (FEAT-INGEST-001)
- reprocessamento idempotente (sem duplicar chunks/vetores)
- chunk rastreável até documento e vetor
- falha marca `failed` com erro

## Consulta (FEAT-QUERY-001)
- resposta cita chunks reais (grounding)
- sem contexto suficiente, sinaliza em vez de alucinar
- filtros por metadado restringem o retrieval

## Global
- respostas sempre com citações
- índice consistente (um modelo/dimensão/métrica por coleção)
