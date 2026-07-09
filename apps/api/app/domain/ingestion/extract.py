"""Extração de texto por família de formato (ADR-0002)."""
from __future__ import annotations

import os

from app.domain.ingestion.errors import PermanentIngestionError

_TEXT_EXT = {".txt", ".md", ".py"}


def extract_text(path: str, filename: str) -> str:
    ext = os.path.splitext(filename or path)[1].lower()
    try:
        if ext in _TEXT_EXT:
            return _read_text(path)
        if ext in {".html", ".htm"}:
            return _extract_html(path)
        if ext == ".pdf":
            return _extract_pdf(path)
        if ext == ".docx":
            return _extract_docx(path)
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


def _extract_pdf(path: str) -> str:
    from pypdf import PdfReader

    reader = PdfReader(path)
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _extract_docx(path: str) -> str:
    import docx

    doc = docx.Document(path)
    return "\n".join(p.text for p in doc.paragraphs)


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
