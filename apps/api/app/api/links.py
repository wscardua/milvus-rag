"""Contrato document-links (ADR-0008): vínculos direcionados e tipados, mesma squad."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import get_session
from app.db.models import LINK_TYPES, Document, DocumentLink
from app.schemas.document import LinkIn, LinkOut

router = APIRouter(tags=["document-links"])


def create_document_link(session: Session, source: Document, data: LinkIn) -> DocumentLink:
    """Cria um vínculo validando tipo, auto-vínculo e restrição de mesma squad (ADR-0008).

    Levanta HTTPException; o commit é responsabilidade do chamador.
    """
    if data.link_type not in LINK_TYPES:
        raise HTTPException(422, f"link_type inválido. Use um de {LINK_TYPES}.")
    if data.target_document_id == source.id:
        raise HTTPException(422, "Documento não pode se vincular a si mesmo.")
    target = session.get(Document, data.target_document_id)
    if not target:
        raise HTTPException(422, "Documento alvo inexistente.")
    if source.delivery_process.squad_id != target.delivery_process.squad_id:
        raise HTTPException(422, "Vínculo permitido apenas entre documentos da mesma squad.")
    link = DocumentLink(
        source_document_id=source.id,
        target_document_id=target.id,
        link_type=data.link_type,
        ordinal=data.ordinal,
    )
    session.add(link)
    return link


@router.get("/documents/{document_id}/links", response_model=list[LinkOut])
def list_links(document_id: uuid.UUID, session: Session = Depends(get_session)):
    if not session.get(Document, document_id):
        raise HTTPException(404, "Documento não encontrado.")
    return session.scalars(
        select(DocumentLink).where(
            or_(
                DocumentLink.source_document_id == document_id,
                DocumentLink.target_document_id == document_id,
            )
        )
    ).all()


@router.post("/documents/{document_id}/links", response_model=LinkOut, status_code=201)
def add_link(document_id: uuid.UUID, payload: LinkIn, session: Session = Depends(get_session)):
    source = session.get(Document, document_id)
    if not source:
        raise HTTPException(404, "Documento não encontrado.")
    link = create_document_link(session, source, payload)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "Vínculo duplicado (mesma origem, alvo e tipo).")
    session.refresh(link)
    return LinkOut.model_validate(link)


@router.delete("/documents/{document_id}/links/{link_id}", status_code=204)
def remove_link(document_id: uuid.UUID, link_id: uuid.UUID, session: Session = Depends(get_session)):
    link = session.get(DocumentLink, link_id)
    if not link or link.source_document_id != document_id:
        raise HTTPException(404, "Vínculo não encontrado para este documento.")
    session.delete(link)
    session.commit()
