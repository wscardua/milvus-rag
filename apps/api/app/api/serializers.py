"""Helpers de serialização compartilhados pelos routers."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document, IngestionJob
from app.schemas.document import DocumentOut


def document_status(session: Session, document_id: uuid.UUID) -> str:
    """Estado do ingestion_job mais recente do documento (fonte do status na UI)."""
    job = session.scalar(
        select(IngestionJob)
        .where(IngestionJob.document_id == document_id)
        .order_by(IngestionJob.created_at.desc())
        .limit(1)
    )
    return job.state if job else "pending"


def to_document_out(session: Session, doc: Document) -> DocumentOut:
    return DocumentOut(
        id=doc.id,
        delivery_process_id=doc.delivery_process_id,
        squad_id=doc.delivery_process.squad_id if doc.delivery_process else None,
        title=doc.title,
        author=doc.author,
        tags=list(doc.tags or []),
        doc_type=doc.doc_type,
        original_filename=doc.original_filename,
        mime_type=doc.mime_type,
        size_bytes=doc.size_bytes,
        category_id=doc.category_id,
        subcategory_id=doc.subcategory_id,
        summary=doc.summary,
        classification_source=doc.classification_source,
        ingested_at=doc.ingested_at,
        status=document_status(session, doc.id),
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )
