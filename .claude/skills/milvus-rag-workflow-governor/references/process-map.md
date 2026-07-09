# Mapa de Processo (leve)

Ordem para mudanças multi-documento na POC de RAG:

1. entrada em `docs/specs/state/status.md` (Trabalho em aberto)
2. feature spec (`docs/specs/features/`)
3. contratos (`docs/specs/contracts/`)
4. arquitetura (`docs/specs/architecture/`)
5. testes (`docs/specs/testing/`)
6. código
7. estado + changelog (de volta em `status.md`)
8. decisões (`docs/specs/decisions/`) quando muda fronteira ou o índice

## Checklist de conclusão

- feature spec reflete o comportamento real
- contratos Django↔FastAPI e o índice Milvus estão coerentes
- testes esperados executados ou pendência registrada
- `status.md` atualizado (status + changelog)
- ADR registrado se mudou fronteira, modelo de embeddings, métrica ou schema
