"""Persistência de arquivos enviados em data/uploads/ (fora do git)."""
from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path

from app.config import settings


def _base_dir() -> Path:
    d = Path(settings.upload_dir).resolve()
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_upload(file_obj, original_filename: str) -> tuple[str, int]:
    """Grava o arquivo com nome único; retorna (caminho_absoluto, tamanho_bytes)."""
    ext = os.path.splitext(original_filename)[1].lower()
    dest = _base_dir() / f"{uuid.uuid4().hex}{ext}"
    with open(dest, "wb") as out:
        shutil.copyfileobj(file_obj, out)
    return str(dest), dest.stat().st_size


def delete_file(path: str | None) -> None:
    """Remove o arquivo do disco; tolerante a caminho vazio ou já ausente."""
    if not path:
        return
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
