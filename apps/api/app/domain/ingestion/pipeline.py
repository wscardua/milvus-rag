"""Pipeline de ingestão (ADR-0004): extração → classificação → chunking → embeddings → índice.

Idempotente por documento: reprocessar apaga chunks/vetores antigos antes de reinserir.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Category, Chunk, Document, Subcategory
from app.domain.ingestion import classify, extract
from app.domain.ingestion.chunking import chunk_text, chunk_params, has_profile
from app.domain.ingestion.errors import PermanentIngestionError
from app.services import embeddings, eventlog, vectorstore

log = logging.getLogger("worker.pipeline")


@dataclass
class IngestStats:
    """Resumo de uma ingestão bem-sucedida — alimenta o log e o `system_log` (ADR-0011)."""
    doc_type: str | None
    profile: str          # "doc_type" quando há perfil específico, senão "global (fallback)"
    text_chars: int
    text_words: int
    chunk_size: int
    chunk_overlap: int
    chunk_count: int
    tokens_min: int
    tokens_avg: int
    tokens_max: int
    vision_enabled: bool
    vectors: int


def _apply_classification(session: Session, doc: Document, text: str) -> None:
    """Best-effort: sugere title/category/subcategory/summary. Falha não interrompe a ingestão."""
    try:
        sug = classify.suggest(session, text, need_title=not doc.title)
        cat = session.scalar(select(Category).where(Category.name == sug.get("category")))
        if cat:
            doc.category_id = cat.id
            doc.subcategory_id = None  # evita manter subcategoria de outra categoria
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
        eventlog.log_event(
            "WARNING",
            "ingestion",
            "llm_classification_failed",
            str(exc),
            document_id=doc.id,
        )


def ingest_document(session: Session, doc: Document) -> IngestStats:
    if settings.vision_enabled:
        log.info("Extração com vision habilitada para %s", doc.original_filename)
    text = extract.extract_text(doc.storage_path, doc.original_filename or "")
    if not text.strip():
        raise PermanentIngestionError("Documento sem texto extraível.")

    _apply_classification(session, doc, text)

    size, overlap = chunk_params(doc.doc_type)
    profile = "doc_type" if has_profile(doc.doc_type) else "global (fallback)"
    log.info(
        "Chunking doc_type=%r perfil=%s → size=%d overlap=%d", doc.doc_type, profile, size, overlap
    )
    chunks = chunk_text(text, size=size, overlap=overlap)
    if not chunks:
        raise PermanentIngestionError("Nenhum chunk gerado.")
    token_counts = [len(c.split()) for c in chunks]

    # embeddings primeiro: se falhar, ainda não apagamos o índice antigo (reduz janela de inconsistência)
    vectors = embeddings.embed_texts(chunks)

    # idempotência: remove chunks/vetores anteriores deste documento só depois de ter os novos vetores
    doc_id = str(doc.id)
    vectorstore.delete_by_document(doc_id)
    for old in session.scalars(select(Chunk).where(Chunk.document_id == doc.id)):
        session.delete(old)
    session.flush()

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
                token_count=token_counts[ordinal],  # já calculado acima; evita re-split
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

    return IngestStats(
        doc_type=doc.doc_type,
        profile=profile,
        text_chars=len(text),
        text_words=len(text.split()),
        chunk_size=size,
        chunk_overlap=overlap,
        chunk_count=len(chunks),
        tokens_min=min(token_counts),
        tokens_avg=round(sum(token_counts) / len(token_counts)),
        tokens_max=max(token_counts),
        vision_enabled=settings.vision_enabled,
        vectors=len(vectors),
    )
