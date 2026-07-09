"""Erros de ingestão. Permanente = não adianta repetir (ADR-0009 → failed imediato)."""


class PermanentIngestionError(Exception):
    """Falha que não deve ser repetida (arquivo inválido/corrompido, sem texto)."""
