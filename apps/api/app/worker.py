"""Daemon de ingestão (ADR-0004 / ADR-0009).

Reivindica jobs da fila `ingestion_job` (SKIP LOCKED), roda o pipeline idempotente,
e aplica retry com backoff + recuperação de jobs presos por visibility timeout.

Executar: python -m app.worker
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, or_, select

from app.config import settings
from app.db.base import SessionLocal
from app.db.models import Document, IngestionJob
from app.domain.ingestion.errors import PermanentIngestionError
from app.domain.ingestion.pipeline import ingest_document

logging.basicConfig(level=logging.INFO, format="%(asctime)s [worker] %(levelname)s %(message)s")
log = logging.getLogger("worker")


def _claim(session):
    """Reivindica um job elegível de forma atômica (ADR-0009)."""
    now = datetime.now(timezone.utc)
    stale = now - timedelta(seconds=settings.worker_visibility_timeout)
    stmt = (
        select(IngestionJob)
        .where(
            or_(
                and_(IngestionJob.state == "pending", IngestionJob.available_at <= now),
                and_(IngestionJob.state == "processing", IngestionJob.heartbeat_at < stale),
            )
        )
        .order_by(IngestionJob.available_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    job = session.scalar(stmt)
    if job is None:
        return None
    job.state = "processing"
    job.started_at = now
    job.heartbeat_at = now
    job.attempts += 1
    session.commit()
    return job


def _process_once(session) -> bool:
    job = _claim(session)
    if job is None:
        return False

    job_id, attempts = job.id, job.attempts
    doc = session.get(Document, job.document_id)
    log.info("Processando job %s (doc %s, tentativa %s)", job_id, job.document_id, attempts)
    try:
        ingest_document(session, doc)
        job.state = "indexed"
        job.error = None
        session.commit()
        log.info("Job %s → indexed", job_id)
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        job = session.get(IngestionJob, job_id)
        permanent = isinstance(exc, PermanentIngestionError)
        if permanent or job.attempts >= settings.worker_max_attempts:
            job.state = "failed"
            log.warning("Job %s → failed (%s): %s", job_id, "permanente" if permanent else "esgotado", exc)
        else:
            backoff = settings.worker_retry_backoff_base * (2 ** (job.attempts - 1))
            job.state = "pending"
            job.available_at = datetime.now(timezone.utc) + timedelta(seconds=backoff)
            log.warning("Job %s → retry em %ss (tentativa %s): %s", job_id, backoff, job.attempts, exc)
        job.error = str(exc)[:2000]
        session.commit()
    return True


def run() -> None:
    log.info(
        "Worker iniciado (poll=%ss, timeout=%ss, max_attempts=%s)",
        settings.worker_poll_interval,
        settings.worker_visibility_timeout,
        settings.worker_max_attempts,
    )
    while True:
        session = SessionLocal()
        try:
            worked = _process_once(session)
        except Exception:  # noqa: BLE001 — nunca deixa o loop morrer
            log.exception("Erro inesperado no loop do worker")
            worked = False
        finally:
            session.close()
        if not worked:
            time.sleep(settings.worker_poll_interval)


if __name__ == "__main__":
    run()
