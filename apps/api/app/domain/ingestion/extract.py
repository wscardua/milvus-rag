"""Extração de texto por família de formato (ADR-0002).

Quando `settings.vision_enabled` (ADR-0012), imagens embutidas em PDF/DOCX são
descritas por LLM vision e intercaladas no texto antes do chunking — de forma
transparente para o pipeline (a assinatura de `extract_text` não muda).
"""
from __future__ import annotations

import logging
import os

from app.config import settings
from app.domain.ingestion.errors import PermanentIngestionError

log = logging.getLogger("worker.extract")

_TEXT_EXT = {".txt", ".md", ".py"}


def extract_text(path: str, filename: str) -> str:
    fname = filename or os.path.basename(path)
    ext = os.path.splitext(fname)[1].lower()
    try:
        if ext in _TEXT_EXT:
            return _read_text(path)
        if ext in {".html", ".htm"}:
            return _extract_html(path)
        if ext == ".pdf":
            return _extract_pdf(path, fname)
        if ext == ".docx":
            return _extract_docx(path, fname)
        if ext in {".xls", ".xlsx"}:
            return _extract_xlsx(path)
    except PermanentIngestionError:
        raise
    except Exception as exc:  # parser falhou → arquivo provavelmente inválido (permanente)
        raise PermanentIngestionError(f"Falha ao extrair {ext}: {exc}") from exc
    raise PermanentIngestionError(f"Extensão não suportada: {ext}")


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _extract_html(path: str) -> str:
    from bs4 import BeautifulSoup

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    return soup.get_text(separator="\n")


def _extract_pdf(path: str, filename: str) -> str:
    from pypdf import PdfReader

    reader = PdfReader(path)

    def _text_only() -> str:
        return "\n".join((page.extract_text() or "") for page in reader.pages)

    if not settings.vision_enabled:
        return _text_only()
    try:
        return _extract_pdf_with_vision(path, filename, reader)
    except Exception as exc:  # noqa: BLE001 — vision é best-effort (ADR-0012): degrada p/ texto
        log.warning("Extração com vision falhou em %s (segue só com texto): %s", filename, exc)
        return _text_only()


def _extract_pdf_with_vision(path: str, filename: str, reader) -> str:
    """Texto via pypdf; imagens embutidas via PyMuPDF (ADR-0012), intercaladas por página.

    Best-effort por página: falha ao abrir/ler uma página não interrompe as demais.
    Deduplica por `xref` — imagem repetida (ex.: logo) reusa a descrição, sem nova chamada.
    """
    import fitz  # PyMuPDF

    from app.services import vision

    parts: list[str] = []
    desc_by_xref: dict[int, str] = {}
    fdoc = fitz.open(path)
    try:
        for page_num, page in enumerate(reader.pages, start=1):
            parts.append(page.extract_text() or "")
            if page_num - 1 >= fdoc.page_count:
                continue
            try:
                fpage = fdoc.load_page(page_num - 1)
                images = fpage.get_images(full=True)
            except Exception:  # noqa: BLE001 — página problemática não interrompe as demais
                continue
            for img in images:
                xref = img[0]
                if xref not in desc_by_xref:
                    image_bytes = _image_png_for_vision(fdoc, fpage, xref)
                    desc_by_xref[xref] = (
                        vision.describe_image(image_bytes, filename, f"página {page_num}")
                        if image_bytes
                        else ""
                    )
                desc = desc_by_xref[xref]
                if desc:
                    parts.append(f"[Imagem — página {page_num}: {desc}]")
    finally:
        fdoc.close()
    return "\n".join(parts)


def _image_png_for_vision(fdoc, fpage, xref) -> bytes | None:
    """PNG da imagem para o vision (ADR-0012). Sempre retorna PNG (casa com o MIME enviado).

    Renderiza a região onde a imagem aparece na página em alta DPI
    (`settings.vision_render_dpi`): normaliza colorspace, captura a imagem como
    exibida e garante tamanho legível — melhor para tabelas/prints densos que o
    bitmap embutido. Fallback: bitmap embutido convertido para PNG (RGB) se não
    houver retângulo de posição.
    """
    import fitz  # PyMuPDF

    try:
        rects = fpage.get_image_rects(xref)
        if rects:
            pix = fpage.get_pixmap(clip=rects[0], dpi=settings.vision_render_dpi)
        else:
            pix = fitz.Pixmap(fdoc, xref)
            if pix.n - pix.alpha >= 4:  # CMYK/separação → RGB para gerar PNG válido
                pix = fitz.Pixmap(fitz.csRGB, pix)
        return pix.tobytes("png")
    except Exception:  # noqa: BLE001 — imagem problemática não interrompe a extração
        return None


def _extract_docx(path: str, filename: str) -> str:
    import docx

    doc = docx.Document(path)
    if not settings.vision_enabled:
        return "\n".join(p.text for p in doc.paragraphs)
    try:
        return _extract_docx_with_vision(doc, filename)
    except Exception as exc:  # noqa: BLE001 — vision é best-effort (ADR-0012): degrada p/ texto
        log.warning("Extração com vision falhou em %s (segue só com texto): %s", filename, exc)
        return "\n".join(p.text for p in doc.paragraphs)


def _extract_docx_with_vision(doc, filename: str) -> str:
    """Texto via python-docx; imagens (blips do XML) descritas por vision (ADR-0012)."""
    from docx.oxml.ns import qn

    from app.services import vision

    part = doc.part
    parts: list[str] = []
    for ordinal, para in enumerate(doc.paragraphs, start=1):
        parts.append(para.text)
        for blip in para._p.findall(".//" + qn("a:blip")):
            rid = blip.get(qn("r:embed"))
            if not rid:
                continue
            try:
                image_bytes = part.related_parts[rid].blob
            except KeyError:  # relação ausente/externa — ignora
                continue
            desc = vision.describe_image(image_bytes, filename, f"parágrafo {ordinal}")
            if desc:
                parts.append(f"[Imagem — parágrafo {ordinal}: {desc}]")
    return "\n".join(parts)


def _extract_xlsx(path: str) -> str:
    from openpyxl import load_workbook

    wb = load_workbook(path, read_only=True, data_only=True)
    lines: list[str] = []
    for ws in wb.worksheets:
        lines.append(f"# {ws.title}")
        for row in ws.iter_rows(values_only=True):
            cells = [str(c) for c in row if c is not None]
            if cells:
                lines.append(" | ".join(cells))
    return "\n".join(lines)
