# Referência — Taxonomia e doc_type

Fonte da verdade das listas de classificação da POC (ADR-0007). Alimenta o **seed** das tabelas `category`/`subcategory` e o enum de `doc_type`, e é a lista **fechada** que a IA pode sugerir na ingestão (FEAT-INGEST-001). O usuário pode trocar o valor sugerido por qualquer outro desta referência (FEAT-WEB-001, `PATCH /documents/{id}`).

> Ao alterar estas listas, atualize este arquivo, registre no changelog de `status.md` e reflita no seed/migrations. Renomear/remover itens em uso deve considerar documentos já classificados.

## 1. Taxonomia temática (`category` → `subcategory`)

Eixo *assunto* do documento, no contexto de delivery de squads. Sugerida pela IA, editável pelo usuário. `subcategory` sempre pertence a uma `category`.

| Categoria | Subcategorias |
|---|---|
| **Produto & Discovery** | Visão de Produto · Requisitos / User Stories · Pesquisa / Discovery · Roadmap |
| **Arquitetura & Engenharia** | Arquitetura de Solução · ADR / Decisão Técnica · APIs & Integrações · Modelo de Dados |
| **Qualidade & Testes** | Estratégia de Testes · Casos de Teste · Critérios de Aceite · Relatório de Bugs |
| **Operações & Infra** | CI/CD · Observabilidade · Runbook / Operação · Infraestrutura |
| **Segurança & Compliance** | Segurança da Informação · LGPD / Privacidade · Auditoria · Gestão de Acessos |
| **Gestão & Processos Ágeis** | Planning · Daily · Review / Demo · Retrospectiva · Refinement · Métricas & Indicadores |
| **Governança & Negócio** | Contratos · SLA / Acordos · Financeiro · Políticas Internas |

## 2. `doc_type` — natureza/formato do artefato

Eixo *tipo* do documento. Escolhido pelo usuário no upload (não sugerido pela IA).

- Documento técnico
- Proposta Técnica
- Manual / Guia
- Procedimento / Runbook
- Especificação / Requisito
- Ata / Registro de reunião
- **Transcrição de reunião** (o tipo de cerimônia — Daily/Planning/Review/Retro/Refinement — é a `subcategory` em *Gestão & Processos Ágeis*)
- Base de Conhecimento
- Apresentação
- Planilha
- Contrato / Documento legal
- Código-fonte
- Relatório
- Outro

## 3. Fase de delivery (`delivery_phase`)

Eixo *etapa do fluxo de entrega* a que o documento se refere (ADR-0014). **Ortogonal** a `delivery_process` (o processo/iniciativa dentro da squad), a `category`/`subcategory` (assunto) e a `doc_type` (natureza). Entrada do usuário (não sugerida pela IA), **opcional** e editável. Lista **fechada**:

- Discovery
- Refinamento Funcional
- Refinamento Técnico
- Desenvolvimento
- Testes
- Release
- Deploy

Filtro na listagem de documentos (`GET /documents?delivery_phase=`). Não entra no índice Milvus nem nos filtros de `/query` (ADR-0014).

## 4. Tipos de vínculo entre documentos (`link_type`)

Lista fixa dos vínculos direcionados (aresta fonte → alvo) entre documentos da **mesma squad** (ADR-0008). A coluna de expansão indica se o alvo entra no contexto do retrieval.

| Tipo | Semântica (fonte → alvo) | Expansão (1 salto) |
|---|---|---|
| `esclarece` | o alvo esclarece/detalha a fonte | inclui o alvo |
| `complementa` | o alvo complementa a fonte | inclui o alvo |
| `precede` | a fonte antecede o alvo no fluxo | inclui o alvo |
| `substitui` | a fonte substitui o alvo (obsoleto) | **exclui/marca** o alvo |

## Regras

- A classificação por IA é **restrita** a esta taxonomia — a IA não cria rótulos novos (mitiga prompt injection; ADR-0007).
- Campos **sugeridos pela IA e editáveis** pelo usuário: `title`, `category`, `subcategory`, `summary`. `doc_type`, squad, processo, `delivery_phase` e `valid_until` são entrada do usuário. `title` é opcional no upload (se vazio, a IA sugere; fallback = nome do arquivo). `delivery_phase` e `valid_until` são opcionais (ADR-0014).
- Estas listas são **seed** — o CRUD de squads/processos (`organization-admin`) não gerencia a taxonomia na POC; alterá-la é mudança de referência (este arquivo).
