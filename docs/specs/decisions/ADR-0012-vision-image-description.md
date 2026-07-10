# ADR-0012 — Descrição de imagens por LLM vision na ingestão

## Contexto
O pipeline de ingestão (FEAT-INGEST-001) extrai apenas o **texto** dos documentos: `_extract_pdf` usa `pypdf` e `_extract_docx` usa `python-docx`, e ambos **descartam as imagens** embutidas. Em documentos de squads de delivery, boa parte da informação está em diagramas de arquitetura, fluxogramas, tabelas em imagem, gráficos e capturas de tela — conteúdo que hoje nunca é indexado no Milvus e, portanto, é invisível ao retrieval.

A stack (ADR-0002) já serve geração por um modelo de chat via LM Studio (API OpenAI-compatível). Modelos como `gemma-3-4b-it-qat` têm capability **Vision**, aceitando imagens no mesmo endpoint `/v1/chat/completions`. Isso permite descrever imagens sem introduzir nova dependência de inferência nem novo serviço — apenas reusando o cliente existente (`app.services.lmstudio.client`).

OCR clássico (Tesseract) foi considerado, mas cobre só texto em imagem; um modelo vision descreve diagramas, gráficos e capturas de forma semântica, alinhado ao objetivo de RAG.

## Decisão
Adicionar um passo **best-effort** de **descrição de imagens por LLM vision** durante a extração, habilitável por env (`VISION_ENABLED`, default `true`):

1. Novo serviço `app/services/vision.py` com `describe_image(image_bytes, filename, position) -> str`, seguindo o padrão de `llm.py`: reusa `lmstudio.client` (mesmo `LM_STUDIO_BASE_URL`/`LM_STUDIO_API_KEY`), modelo configurável por `VISION_MODEL`, `max_tokens` por `VISION_MAX_TOKENS`, `temperature=0`. Envia a imagem como `image_url` base64 (`data:image/...;base64,...`). **Falha retorna `""`** (não interrompe a ingestão).
2. `_extract_pdf`/`_extract_docx` (em `extract.py`) passam a extrair as imagens embutidas (PDF via **PyMuPDF/fitz**; DOCX via relações do `python-docx`), chamar o serviço vision e **intercalar** a descrição no texto no formato `[Imagem — página N: {descrição}]` (PDF) / `[Imagem — parágrafo N: {descrição}]` (DOCX), **antes do chunking**.
3. A assinatura de `extract.extract_text(path, filename) -> str` **permanece inalterada** — o vision é transparente para o `pipeline.py`. O chunking, embeddings e indexação seguem idênticos.
4. Tudo por env (ADR-0006): `VISION_ENABLED`/`VISION_MODEL`/`VISION_MAX_TOKENS`/`VISION_RENDER_DPI` em `config.py`, nada hardcoded fora dele.

### Medidas de acurácia (contra alucinação em tabelas/prints densos)
Validação com PDF real (slides de PI Planning, tabelas coladas como imagem) mostrou que um modelo vision pequeno (`gemma-3-4b-it-qat`) **alucinava** conteúdo inexistente em imagens densas. Três ajustes reduziram o risco, mantendo o modelo:
- **Prompt estrito de fidelidade** (invariável, em `vision.py`): transcrever SOMENTE o visível; não inferir/completar; marcar `[ilegível]` em vez de adivinhar. Eliminou a fabricação de conteúdo.
- **`VISION_MAX_TOKENS` default 300 → 800**: tabelas densas deixam de truncar.
- **`VISION_RENDER_DPI` (default 200)**: em vez de enviar o bitmap embutido, renderiza a **região da imagem na página** em alta DPI (`page.get_image_rects` + `get_pixmap(clip=..., dpi=...)`) — normaliza colorspace, captura a imagem como exibida e garante tamanho legível. Fallback para o bitmap embutido se não houver retângulo.

Resíduo aceito: modelos vision pequenos ainda cometem erros de OCR em células densas; para máxima fidelidade, trocar `VISION_MODEL` por um modelo maior/tuned p/ documento (só `.env`).

O conteúdo da imagem é tratado como **entrada não confiável** (mesmo princípio da classificação — ADR-0007): o system prompt instrui o modelo a ignorar instruções contidas na imagem, e o conteúdo bruto não vai para logs.

## Impacto
- **Sem mudança no contrato do índice** (ADR-0002): modelo/dimensão/métrica de embeddings inalterados (768/COSINE). As descrições entram como texto comum, chunkado e vetorizado como o resto.
- **Sem mudança de schema**: nenhuma migration; nenhum campo novo no Postgres nem no payload do Milvus.
- **Nova dependência: PyMuPDF (`pymupdf`)**, licenciada sob **AGPL-3.0**. Trade-off **aceito para a POC** (uso interno, não distribuído). Caso a POC evolua para produto distribuído, reavaliar: trocar por extrator de imagens com licença permissiva ou adquirir licença comercial da Artifex. O `pypdf` (BSD) é mantido para o **texto**; o PyMuPDF é usado **apenas para extrair imagens** do PDF.
- **Custo/latência**: cada imagem gera uma chamada ao LM Studio. Mitigado por: flag de desligar (`VISION_ENABLED=false` → zero overhead), `max_tokens` curto (default 300) e natureza best-effort.
- Afeta **FEAT-INGEST-001** (bump para v0.9.0). Não afeta `apps/web`, `apps/mcp` nem os testes existentes.

## Alternativas rejeitadas
- **OCR (Tesseract)**: só transcreve texto em imagem; não descreve diagramas/gráficos/arquitetura semanticamente. Fora da POC.
- **Flag/serviço de inferência separado para vision**: violaria ADR-0002/0006 (novo serviço, config duplicada). Reusar o LM Studio e o cliente existente é mais simples e coerente.
- **Mudar a assinatura de `extract_text` para retornar `(texto, imagens[])`**: vazaria a responsabilidade de orquestrar vision para o `pipeline.py`. Manter a intercalação dentro dos extratores mantém o pipeline intocado.
- **Persistir as imagens/descrições em nova tabela**: exigiria schema novo e migration; desnecessário para a POC — a descrição textual intercalada já é indexada e rastreável pelo chunk que a contém.

## Data
2026-07-10

## Status
aceita
