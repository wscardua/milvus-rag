"""Chunking adaptativo por doc_type (ADR-0013) — unitário puro, sem infra.

Trava a tabela de perfis: os valores aqui DEVEM bater com config.py e o ADR-0013.
"""
from __future__ import annotations

import pytest

from app.config import settings
from app.domain.ingestion.chunking import chunk_params, chunk_text

# doc_type → (size, overlap) esperados (fonte da verdade: ADR-0013)
PROFILES = {
    "Procedimento / Runbook":     (150, 20),
    "Transcrição de reunião":     (200, 50),
    "Ata / Registro de reunião":  (200, 40),
    "Código-fonte":               (120, 15),
    "Planilha":                   (80, 10),
    "Contrato / Documento legal": (500, 100),
    "Manual / Guia":              (400, 80),
    "Relatório":                  (400, 70),
    "Documento técnico":          (350, 60),
    "Proposta Técnica":           (300, 60),
    "Especificação / Requisito":  (300, 60),
    "Base de Conhecimento":       (350, 60),
    "Apresentação":               (300, 50),
}


@pytest.mark.parametrize("doc_type,expected", PROFILES.items())
def test_chunk_params_por_doc_type(doc_type, expected):
    assert chunk_params(doc_type) == expected


@pytest.mark.parametrize("doc_type", ["Outro", None, "Tipo Inexistente"])
def test_chunk_params_fallback_global(doc_type):
    assert chunk_params(doc_type) == (settings.chunk_size_words, settings.chunk_overlap_words)


def test_chunk_params_respeita_env(monkeypatch):
    """Sobrescrever a variável no settings muda o perfil sem mudança de código (ADR-0006)."""
    monkeypatch.setattr(settings, "chunk_size_planilha", 100, raising=False)
    assert chunk_params("Planilha") == (100, 10)


def test_chunk_text_usa_size_menor_gera_mais_chunks():
    text = " ".join(str(i) for i in range(300))
    poucos = chunk_text(text, size=200, overlap=50)
    muitos = chunk_text(text, size=80, overlap=10)
    assert len(muitos) > len(poucos)
