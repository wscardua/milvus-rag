# ADR-0013 — Chunking adaptativo por doc_type (e doc_type obrigatório no upload)

## Contexto
O chunking uniforme (350 palavras / 60 de overlap — `chunk_size_words`/`chunk_overlap_words`) ignora a estrutura natural de cada tipo de documento: runbooks têm passos curtos e autossuficientes, transcrições têm falas curtas com mudança de assunto frequente, planilhas têm linhas de dados sem dependência narrativa, contratos têm cláusulas longas com contexto hierárquico. Um tamanho único produz chunks ruins para a maioria dos tipos, prejudicando diretamente a qualidade do retrieval e das citações.

Além disso, `doc_type` era opcional no upload, criando uma dependência circular: o chunking ocorre na ingestão assíncrona (FEAT-INGEST-001), mas a classificação por IA também ocorre na mesma ingestão — portanto o `doc_type` nunca estaria disponível em tempo de chunking se dependesse da IA. Tornar `doc_type` obrigatório no upload resolve essa dependência (a taxonomia já define que `doc_type` é entrada do usuário, não sugerida pela IA — ver [reference/taxonomy.md](../reference/taxonomy.md)).

Esta mudança afeta o retrieval (o tamanho dos chunks impacta diretamente a qualidade das citações) — gatilho obrigatório de ADR conforme `CLAUDE.md`.

## Decisão
Perfis de parâmetros `(size, overlap)` por `doc_type`, todos configuráveis via variáveis de ambiente seguindo o padrão `CHUNK_SIZE_<SLUG>` / `CHUNK_OVERLAP_<SLUG>` (ADR-0006). **Fallback** para `chunk_size_words` / `chunk_overlap_words` (config global) quando o `doc_type` não tem configuração específica (ex.: `Outro`) ou é `None` — nunca lança exceção por `doc_type` desconhecido.

Perfis default (codificados no `config.py`, todos sobrescrevíveis por env sem mudança de código):

| doc_type                    | SLUG                     | size | overlap |
|-----------------------------|--------------------------|------|---------|
| Procedimento / Runbook      | PROCEDIMENTO_RUNBOOK     |  150 |      20 |
| Transcrição de reunião      | TRANSCRICAO_REUNIAO      |  200 |      50 |
| Ata / Registro de reunião   | ATA_REUNIAO              |  200 |      40 |
| Código-fonte                | CODIGO_FONTE             |  120 |      15 |
| Planilha                    | PLANILHA                 |   80 |      10 |
| Contrato / Documento legal  | CONTRATO_LEGAL           |  500 |     100 |
| Manual / Guia               | MANUAL_GUIA              |  400 |      80 |
| Relatório                   | RELATORIO                |  400 |      70 |
| Documento técnico           | DOCUMENTO_TECNICO        |  350 |      60 |
| Proposta Técnica            | PROPOSTA_TECNICA         |  300 |      60 |
| Especificação / Requisito   | ESPECIFICACAO_REQUISITO  |  300 |      60 |
| Base de Conhecimento        | BASE_CONHECIMENTO        |  350 |      60 |
| Apresentação                | APRESENTACAO             |  300 |      50 |
| Outro                       | —                        | fallback global | fallback global |

`doc_type` obrigatório no upload via API (`Form(...)` obrigatório) e UI Django (`required` no select + validação na view). O banco permanece nullable (`Mapped[str | None]`) para retrocompatibilidade — a obrigatoriedade é regra de negócio na API, não constraint do Postgres. `DocumentOut.doc_type` permanece `str | None` para não quebrar clientes que consomem documentos já existentes sem `doc_type`.

Documentos já indexados **não** são reindexados — o chunking antigo permanece até eventual reprocessamento manual.

## Impacto
- **FEAT-INGEST-001** (0.9.0 → 0.10.0): chunking passa a usar perfil por `doc_type`; fallback global para tipos sem perfil ou `None`.
- **FEAT-UPLOAD-001** (0.4.0 → 0.5.0): `doc_type` obrigatório no upload.
- `config.py`: novas variáveis por `doc_type` (tudo por env — ADR-0006).
- Contrato `upload-and-metadata`: `doc_type` muda de opcional para obrigatório; erro `422` quando ausente ou fora da taxonomia.
- `query_log` já registra `chunk_size_words`/`chunk_overlap_words` no momento da consulta — captura o perfil efetivo sem mudança de schema.
- **Sem migration de banco**; **sem mudança no índice Milvus**; **sem mudança no contrato de embeddings** (modelo/dimensão/métrica intocados — ADR-0002).

## Alternativas rejeitadas
- **Estratégias de splitting distintas por família** (separar por `def`/`class` para código, por heading para specs): mais potente, mas exige avaliação de retrieval para justificar; rejeitado para a POC — reavaliar após golden set de perguntas.
- **Manter `doc_type` opcional e aplicar perfil após classificação por IA**: cria dependência circular (o chunking já ocorreu quando a IA classifica na mesma ingestão). Rejeitado.
- **Arquivo JSON externo para os perfis**: aumenta a complexidade operacional (novo arquivo a gerenciar, caminho a configurar); variáveis de env por `doc_type` são suficientes para a POC e seguem o padrão já estabelecido pelo ADR-0006. Rejeitado para a POC.

## Data
2026-07-10

## Status
aceita
