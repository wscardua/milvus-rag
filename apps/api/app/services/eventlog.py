"""Log de eventos do sistema no Postgres (ADR-0011).

`log_event` grava uma linha em `system_log` numa sessão própria e curta, isolada da
transação do chamador — assim um rollback do fluxo principal não perde o log, e uma
falha ao logar nunca derruba o fluxo (best-effort).
"""
from __future__ import annotations

import logging
import uuid

from app.db.base import SessionLocal
from app.db.models import SystemLog

_fallback = logging.getLogger("eventlog")


def log_event(
    level: str,
    component: str,
    event: str,
    message: str | None = None,
    *,
    document_id: uuid.UUID | str | None = None,
    job_id: uuid.UUID | str | None = None,
    **context,
) -> None:
    """Persiste um evento estruturado. Nunca propaga exceção."""
    session = SessionLocal()
    try:
        session.add(
            SystemLog(
                level=level,
                component=component,
                event=event,
                message=(message[:4000] if message else None),
                context=(context or None),
                document_id=_as_uuid(document_id),
                job_id=_as_uuid(job_id),
            )
        )
        session.commit()
    except Exception:  # noqa: BLE001 — logar nunca pode quebrar o fluxo principal
        session.rollback()
        _fallback.exception("Falha ao gravar system_log (%s/%s/%s)", level, component, event)
    finally:
        session.close()


def _as_uuid(value: uuid.UUID | str | None) -> uuid.UUID | None:
    if value is None or isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None
