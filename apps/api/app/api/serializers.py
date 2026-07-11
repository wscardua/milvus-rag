"""Helpers de serialização compartilhados pelos routers."""
from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentLink, IngestionJob
from app.schemas.document import DocumentOut, LinksSummary


def document_status(session: Session, document_id: uuid.UUID) -> str:
    """Estado do ingestion_job mais recente do documento (fonte do status na UI)."""
    job = session.scalar(
        select(IngestionJob)
        .where(IngestionJob.document_id == document_id)
        .order_by(IngestionJob.created_at.desc())
        .limit(1)
    )
    return job.state if job else "pending"


def fetch_links_summary(session: Session, document_ids: list[uuid.UUID]) -> dict[uuid.UUID, LinksSummary]:
    """Agregado (count + tipos) de vínculos por documento, em 1 query — evita N+1 na listagem.

    Bidirecional (ADR-0008): conta vínculos onde o documento é origem ou alvo, mesma
    semântica de `list_links` (apps/api/app/api/links.py).
    """
    if not document_ids:
        return {}
    id_set = set(document_ids)
    rows = session.execute(
        select(DocumentLink.source_document_id, DocumentLink.target_document_id, DocumentLink.link_type).where(
            or_(DocumentLink.source_document_id.in_(document_ids), DocumentLink.target_document_id.in_(document_ids))
        )
    ).all()
    counts: dict[uuid.UUID, int] = {}
    types: dict[uuid.UUID, set[str]] = {}
    for source_id, target_id, link_type in rows:
        for doc_id in {source_id, target_id} & id_set:
            counts[doc_id] = counts.get(doc_id, 0) + 1
            types.setdefault(doc_id, set()).add(link_type)
    return {doc_id: LinksSummary(count=count, types=sorted(types[doc_id])) for doc_id, count in counts.items()}


def to_document_out(session: Session, doc: Document, links_summary: LinksSummary | None = None) -> DocumentOut:
    if links_summary is None:
        links_summary = fetch_links_summary(session, [doc.id]).get(doc.id, LinksSummary())
    return DocumentOut(
        id=doc.id,
        delivery_process_id=doc.delivery_process_id,
        squad_id=doc.delivery_process.squad_id if doc.delivery_process else None,
        title=doc.title,
        author=doc.author,
        tags=list(doc.tags or []),
        doc_type=doc.doc_type,
        delivery_phase=doc.delivery_phase,
        valid_until=doc.valid_until,
        original_filename=doc.original_filename,
        mime_type=doc.mime_type,
        size_bytes=doc.size_bytes,
        category_id=doc.category_id,
        subcategory_id=doc.subcategory_id,
        summary=doc.summary,
        classification_source=doc.classification_source,
        ingested_at=doc.ingested_at,
        status=document_status(session, doc.id),
        links_summary=links_summary,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )
