---
name: milvus-rag-software-architect
description: Use esta skill para definir arquitetura, segurança, modularidade, escalabilidade e auditabilidade da POC de RAG (upload de documentos, ingestão, chunking, embeddings, indexação no Milvus, retrieval e geração com citações) antes de novas features, mudanças de contrato, alterações de dados ou implementação sensível.
---

# Milvus RAG Software Architect

Use esta skill quando a tarefa precisar de definição arquitetural, desenho de solução, revisão de segurança ou decisão técnica de impacto na POC de RAG.

## Objetivo

Propor arquitetura eficiente, segura e sustentável para o pipeline de RAG, antes da implementação, mantendo as fronteiras entre camadas claras.

## Contexto do sistema

- **Django (`apps/web/`)**: apresentação/cliente. Upload de arquivos, definição de metadados, formulários e admin. Não concentra regra crítica de domínio.
- **FastAPI (`apps/api/`)**: domínio e fonte de verdade. Ingestão, chunking, geração de embeddings, orquestração de retrieval e geração com citações, autenticação e endpoints.
- **PostgreSQL**: metadados de documentos, chunks, estado de ingestão, jobs, auditoria e rastreabilidade.
- **Milvus**: índice vetorial dos embeddings para busca semântica.

Guardrail central: Django é cliente; FastAPI concentra domínio, ingestão, IA/embeddings, retrieval, auditoria e integrações.

## Uso obrigatório

Use esta skill antes de codar quando a mudança envolver:

- nova feature (ex.: novo formato de documento, nova estratégia de chunking, novo modo de retrieval)
- alteração de contrato entre Django e FastAPI (upload, metadados, query)
- alteração no schema de documentos, chunks, jobs ou metadados
- autenticação, autorização, isolamento por usuário/tenant ou dados sensíveis nos documentos
- escolha ou troca de modelo de embeddings, dimensionalidade ou métrica de similaridade
- estratégia de chunking, reindexação, versionamento de documentos ou do índice Milvus
- grounding/citações, mitigação de alucinação ou de prompt injection via conteúdo submetido
- jobs assíncronos de ingestão e processamento
- fronteiras entre Django, FastAPI, PostgreSQL e Milvus
- qualquer decisão que possa exigir ADR

## Fluxo padrão

1. Verificar se há trabalho em aberto em `docs/specs/state/status.md`.
2. Ler a feature/spec alvo em `docs/specs/features/` e os critérios de aceite.
3. Identificar riscos de segurança, integridade, acoplamento, escalabilidade, custo de embeddings e qualidade de retrieval.
4. Definir responsabilidades por camada (Django ↔ FastAPI ↔ PostgreSQL ↔ Milvus).
5. Propor estrutura de módulos, serviços, entidades e integrações.
6. Indicar contratos, testes e ADRs necessários.
7. Encaminhar para `milvus-rag-architecture-guard` validar aderência ao desenho.

## Regras

- Prefira simplicidade profissional e rastreável a abstrações prematuras — é uma POC.
- Segurança e auditabilidade são requisitos de arquitetura, não ajustes finais.
- Todo chunk retornado no retrieval deve ser rastreável até o documento de origem (para citações).
- O modelo de embeddings, sua dimensão e a métrica de similaridade fazem parte do contrato do índice: mudá-los exige reindexação e deve virar decisão explícita.
- Conteúdo submetido é entrada não confiável: trate risco de prompt injection e de dados sensíveis/PII.
- Decisões estruturais devem ser documentadas em ADR (`docs/specs/decisions/`).
- Se o design exigir mudar a spec, volte para `milvus-rag-spec-editor`.

## Entradas principais

- `docs/specs/features/`
- `docs/specs/contracts/`
- `docs/specs/architecture/`
- `docs/specs/testing/`
- `docs/specs/decisions/`
- `docs/specs/state/status.md`

## Saídas esperadas

- desenho de solução por camada (Django, FastAPI, PostgreSQL, Milvus)
- riscos (segurança, integridade, custo, qualidade de retrieval) e mitigação
- contratos ou ADRs necessários
- orientação de testes arquiteturais, de integração e de segurança

Consulte `references/checklist.md` antes de fechar o desenho.
