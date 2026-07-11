"""Reenfileiramento do acervo p/ popular delivery_phase/tags no Milvus (ADR-0015).

Recomendado, não bloqueante: documentos já `indexed` antes do WORK-010 não têm
`delivery_phase`/`tags` no payload do Milvus (campo dinâmico) até serem reprocessados —
a busca sem esses filtros continua funcionando normalmente enquanto isso não roda.

Cria um novo `ingestion_job` (state=pending) para cada documento em `indexed`, reusando o
mesmo mecanismo do upload (`documents.py:upload_document`) e o pipeline idempotente do worker
(apaga chunks/vetores antigos antes de reinserir — não duplica). Precisa do worker rodando
(`python -m app.worker`) para os jobs serem processados.

Rode com:
    python -m app.db.reindex_dynamic_fields
"""
from __future__ import annotations

import logging

from sqlalchemy import select

from app.api.serializers import document_status
from app.db.base import SessionLocal
from app.db.models import Document, IngestionJob

logging.basicConfig(level=logging.INFO, format="%(asctime)s [reindex] %(levelname)s %(message)s")
log = logging.getLogger("reindex")


def enqueue_reindex() -> int:
    """Enfileira um novo job `pending` para todo documento cujo estado atual é `indexed`."""
    session = SessionLocal()
    try:
        doc_ids = session.scalars(select(Document.id)).all()
        to_enqueue = [doc_id for doc_id in doc_ids if document_status(session, doc_id) == "indexed"]
        for doc_id in to_enqueue:
            session.add(IngestionJob(document_id=doc_id, state="pending"))
        session.commit()
        return len(to_enqueue)
    finally:
        session.close()


if __name__ == "__main__":
    count = enqueue_reindex()
    log.info("Reenfileirados %d documentos já indexados (delivery_phase/tags, ADR-0015).", count)
