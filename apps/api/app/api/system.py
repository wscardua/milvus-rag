"""Observabilidade (ADR-0011): /health detalhado por serviço e /logs (system_log).

Contrato logs-and-health. A UI Django consome estes endpoints — nunca lê Postgres/Milvus direto.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.config import settings
from app.db.base import get_session
from app.db.models import IngestionJob, SystemLog
from app.services import vectorstore
from app.services.lmstudio import client

router = APIRouter(tags=["system"])


def _check_postgres(session: Session) -> dict:
    try:
        session.execute(text("SELECT 1"))
        return {"name": "postgres", "ok": True, "detail": "conectado"}
    except Exception as exc:  # noqa: BLE001
        return {"name": "postgres", "ok": False, "detail": str(exc)[:200]}


def _check_milvus() -> dict:
    try:
        exists = vectorstore.ping()  # não cria a coleção (health é somente-leitura)
        detail = f"coleção {settings.milvus_collection}" + ("" if exists else " ausente")
        return {"name": "milvus", "ok": exists, "detail": detail}
    except Exception as exc:  # noqa: BLE001
        return {"name": "milvus", "ok": False, "detail": str(exc)[:200]}


def _check_lm_studio() -> dict:
    try:
        models = client.models.list()
        ids = [m.id for m in models.data][:5]
        return {"name": "lm_studio", "ok": True, "detail": f"modelos: {', '.join(ids) or 'nenhum'}"}
    except Exception as exc:  # noqa: BLE001
        return {"name": "lm_studio", "ok": False, "detail": str(exc)[:200]}


def _check_worker(session: Session) -> dict:
    """Liveness derivada: heartbeat recente no system_log + jobs presos (ADR-0009/0011)."""
    now = datetime.now(timezone.utc)
    window = now - timedelta(seconds=settings.worker_heartbeat_interval * 3)
    last = session.scalar(
        select(func.max(SystemLog.ts)).where(SystemLog.component == "worker")
    )
    alive = last is not None and last >= window
    stuck = session.scalar(
        select(func.count(IngestionJob.id)).where(
            IngestionJob.state == "processing",
            IngestionJob.heartbeat_at < now - timedelta(seconds=settings.worker_visibility_timeout),
        )
    ) or 0
    detail = f"último sinal: {last.isoformat() if last else 'nunca'}; presos: {stuck}"
    return {"name": "worker", "ok": bool(alive) and stuck == 0, "detail": detail}


@router.get("/health")
def health(session: Session = Depends(get_session)):
    """Saúde por serviço + profundidade da fila de ingestão."""
    rows = session.execute(
        select(IngestionJob.state, func.count(IngestionJob.id)).group_by(IngestionJob.state)
    ).all()
    queue = {state: 0 for state in ("pending", "processing", "indexed", "failed")}
    for state, count in rows:
        queue[state] = count

    components = [
        _check_postgres(session),
        _check_milvus(),
        _check_lm_studio(),
        _check_worker(session),
    ]
    status = "ok" if all(c["ok"] for c in components) else "degraded"
    return {"status": status, "components": components, "queue": queue}


@router.get("/logs")
def list_logs(
    response: Response,
    level: str | None = None,
    component: str | None = None,
    since: datetime | None = None,
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    """Lista eventos do system_log, mais recentes primeiro, com filtros e paginação (WORK-007)."""
    stmt = select(SystemLog)
    if level:
        stmt = stmt.where(SystemLog.level == level)
    if component:
        stmt = stmt.where(SystemLog.component == component)
    if since:
        stmt = stmt.where(SystemLog.ts >= since)

    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    response.headers["X-Total-Count"] = str(total)

    logs = session.scalars(stmt.order_by(SystemLog.ts.desc()).limit(limit).offset(offset)).all()
    return [
        {
            "id": str(lg.id),
            "ts": lg.ts.isoformat(),
            "level": lg.level,
            "component": lg.component,
            "event": lg.event,
            "message": lg.message,
            "context": lg.context,
            "document_id": str(lg.document_id) if lg.document_id else None,
            "job_id": str(lg.job_id) if lg.job_id else None,
        }
        for lg in logs
    ]
