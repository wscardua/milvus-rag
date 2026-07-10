"""Chunking por janelas de palavras com overlap (default configurável, chunk < 2048 tokens)."""
from __future__ import annotations

from app.config import settings

# Mapeia o doc_type (taxonomia — reference/taxonomy.md) para o slug das variáveis de settings.
# Os números vivem no config.py (ADR-0006). "Outro" e qualquer valor fora desta lista
# caem no fallback global (chunk_size_words / chunk_overlap_words).
_DOC_TYPE_TO_SLUG: dict[str, str] = {
    "Procedimento / Runbook":     "procedimento_runbook",
    "Transcrição de reunião":     "transcricao_reuniao",
    "Ata / Registro de reunião":  "ata_reuniao",
    "Código-fonte":               "codigo_fonte",
    "Planilha":                   "planilha",
    "Contrato / Documento legal": "contrato_legal",
    "Manual / Guia":              "manual_guia",
    "Relatório":                  "relatorio",
    "Documento técnico":          "documento_tecnico",
    "Proposta Técnica":           "proposta_tecnica",
    "Especificação / Requisito":  "especificacao_requisito",
    "Base de Conhecimento":       "base_conhecimento",
    "Apresentação":               "apresentacao",
    # "Outro" e qualquer valor não listado: fallback para defaults globais
}

# Fail-fast (ADR-0006/ADR-0013): todo slug mapeado precisa ter os dois campos no settings.
# Sem isto, chunk_params cairia silenciosamente no default global e ainda reportaria
# perfil=doc_type no log — mascarando uma desync entre o mapeamento e o config.py.
_missing_chunk_fields = [
    f"{prefix}{slug}"
    for slug in set(_DOC_TYPE_TO_SLUG.values())
    for prefix in ("chunk_size_", "chunk_overlap_")
    if not hasattr(settings, f"{prefix}{slug}")
]
if _missing_chunk_fields:
    raise RuntimeError(
        "Config de chunking ausente para doc_type mapeado em _DOC_TYPE_TO_SLUG: "
        f"{_missing_chunk_fields}"
    )


def has_profile(doc_type: str | None) -> bool:
    """True se o doc_type tem perfil de chunking próprio (senão usa o fallback global)."""
    return (doc_type or "") in _DOC_TYPE_TO_SLUG


def chunk_params(doc_type: str | None) -> tuple[int, int]:
    """Retorna (size, overlap) para o doc_type dado (ADR-0013).

    Lê de settings (ADR-0006: tudo por env). Fallback para os defaults globais
    (chunk_size_words / chunk_overlap_words) quando o doc_type não tem configuração
    específica ou quando doc_type é None. Nunca lança por doc_type desconhecido.
    """
    slug = _DOC_TYPE_TO_SLUG.get(doc_type or "")
    if slug:
        size = getattr(settings, f"chunk_size_{slug}", settings.chunk_size_words)
        overlap = getattr(settings, f"chunk_overlap_{slug}", settings.chunk_overlap_words)
        return size, overlap
    return settings.chunk_size_words, settings.chunk_overlap_words


def chunk_text(text: str, size: int | None = None, overlap: int | None = None) -> list[str]:
    size = size or settings.chunk_size_words
    overlap = overlap or settings.chunk_overlap_words
    words = text.split()
    if not words:
        return []
    step = max(1, size - overlap)
    chunks: list[str] = []
    i = 0
    while i < len(words):
        chunks.append(" ".join(words[i : i + size]))
        if i + size >= len(words):
            break
        i += step
    return chunks
