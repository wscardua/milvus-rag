"""Pipeline de ingestão (ADR-0004): extração → classificação → chunking → embeddings → índice.

Idempotente por documento: reprocessar apaga chunks/vetores antigos antes de reinserir.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Category, Chunk, Document, Subcategory
from app.domain.ingestion import classify, extract
from app.domain.ingestion.chunking import chunk_text
from app.domain.ingestion.errors import PermanentIngestionError
from app.services import embeddings, vectorstore

log = logging.getLogger("worker.pipeline")


def _apply_classification(session: Session, doc: Document, text: str) -> None:
    """Best-effort: sugere title/category/subcategory/summary. Falha não interrompe a ingestão."""
    try:
        sug = classify.suggest(session, text, need_title=not doc.title)
        cat = session.scalar(select(Category).where(Category.name == sug.get("category")))
        if cat:
            doc.category_id = cat.id
            sub = session.scalar(
                select(Subcategory).where(
                    Subcategory.category_id == cat.id, Subcategory.name == sug.get("subcategory")
                )
            )
            if sub:
                doc.subcategory_id = sub.id
        if sug.get("summary"):
            doc.summary = sug["summary"]
        if not doc.title and sug.get("title"):
            doc.title = sug["title"]
        doc.classification_source = "llm"
    except Exception as exc:  # noqa: BLE001 — classificação é best-effort
        log.warning("Classificação por IA falhou (segue sem): %s", exc)


def ingest_document(session: Session, doc: Document) -> None:
    text = extract.extract_text(doc.storage_path, doc.original_filename or "")
    if not text.strip():
        raise PermanentIngestionError("Documento sem texto extraível.")

    _apply_classification(session, doc, text)

    chunks = chunk_text(text)
    if not chunks:
        raise PermanentIngestionError("Nenhum chunk gerado.")

    # idempotência: remove chunks/vetores anteriores deste documento
    doc_id = str(doc.id)
    vectorstore.delete_by_document(doc_id)
    for old in session.scalars(select(Chunk).where(Chunk.document_id == doc.id)):
        session.delete(old)
    session.flush()

    vectors = embeddings.embed_texts(chunks)
    squad_id = str(doc.delivery_process.squad_id)
    rows = []
    for ordinal, (content, vector) in enumerate(zip(chunks, vectors)):
        cid = uuid.uuid4()
        session.add(
            Chunk(
                id=cid,
                document_id=doc.id,
                ordinal=ordinal,
                text=content,
                milvus_vector_id=cid.hex,
                token_count=len(content.split()),
            )
        )
        rows.append(
            {
                "chunk_id": cid.hex,
                "vector": vector,
                "document_id": doc_id,
                "squad_id": squad_id,
                "delivery_process_id": str(doc.delivery_process_id),
                "category_id": str(doc.category_id) if doc.category_id else "",
                "doc_type": doc.doc_type or "",
            }
        )
    vectorstore.upsert_chunks(rows)
    doc.ingested_at = datetime.now(timezone.utc)
