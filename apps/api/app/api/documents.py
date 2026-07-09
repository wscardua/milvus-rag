"""Contrato upload-and-metadata (ADR-0007): upload, listagem, detalhe e overrides."""
from __future__ import annotations

import json
import os
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.links import create_document_link
from app.api.serializers import to_document_out
from app.config import settings
from app.db.base import get_session
from app.db.models import (
    ALLOWED_EXTENSIONS,
    DOC_TYPES,
    Category,
    DeliveryProcess,
    Document,
    IngestionJob,
    Subcategory,
)
from app.schemas.document import DocumentOut, DocumentUpdate, LinkIn
from app.services import storage

router = APIRouter(tags=["documents"])


@router.post("/documents", response_model=DocumentOut, status_code=201)
def upload_document(
    file: UploadFile = File(...),
    delivery_process_id: uuid.UUID = Form(...),
    title: str | None = Form(None),
    author: str | None = Form(None),
    doc_type: str | None = Form(None),
    tags: str | None = Form(None),  # separadas por vírgula
    links: str | None = Form(None),  # JSON: [{"target_document_id","link_type","ordinal"}]
    session: Session = Depends(get_session),
):
    process = session.get(DeliveryProcess, delivery_process_id)
    if not process:
        raise HTTPException(422, "Processo de delivery inexistente.")

    if doc_type is not None and doc_type not in DOC_TYPES:
        raise HTTPException(422, f"doc_type inválido. Use um de {DOC_TYPES}.")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(415, f"Tipo não suportado. Aceitos: {ALLOWED_EXTENSIONS}.")

    storage_path, size_bytes = storage.save_upload(file.file, file.filename or "arquivo")
    if size_bytes > settings.max_upload_mb * 1024 * 1024:
        os.remove(storage_path)
        raise HTTPException(413, f"Arquivo excede {settings.max_upload_mb} MB.")

    tag_list = [t.strip() for t in tags.split(",")] if tags else []
    tag_list = [t for t in tag_list if t]

    doc = Document(
        delivery_process_id=delivery_process_id,
        title=(title.strip() if title and title.strip() else None),
        author=author,
        tags=tag_list,
        doc_type=doc_type,
        original_filename=file.filename,
        mime_type=file.content_type,
        size_bytes=size_bytes,
        storage_path=storage_path,
    )
    session.add(doc)
    session.flush()  # garante doc.id e carrega delivery_process p/ validação de vínculo

    if links:
        try:
            items = json.loads(links)
        except json.JSONDecodeError:
            raise HTTPException(422, "Campo 'links' deve ser um JSON válido.")
        for item in items:
            create_document_link(session, doc, LinkIn(**item))

    session.add(IngestionJob(document_id=doc.id, state="pending"))
    session.commit()
    session.refresh(doc)
    return to_document_out(session, doc)


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(
    squad_id: uuid.UUID | None = None,
    delivery_process_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
    doc_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_session),
):
    stmt = select(Document).order_by(Document.created_at.desc())
    if squad_id:
        stmt = stmt.join(DeliveryProcess, Document.delivery_process_id == DeliveryProcess.id).where(
            DeliveryProcess.squad_id == squad_id
        )
    if delivery_process_id:
        stmt = stmt.where(Document.delivery_process_id == delivery_process_id)
    if category_id:
        stmt = stmt.where(Document.category_id == category_id)
    if doc_type:
        stmt = stmt.where(Document.doc_type == doc_type)
    docs = session.scalars(stmt.limit(min(limit, 200)).offset(offset)).all()
    return [to_document_out(session, d) for d in docs]


@router.get("/documents/{document_id}", response_model=DocumentOut)
def get_document(document_id: uuid.UUID, session: Session = Depends(get_session)):
    doc = session.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Documento não encontrado.")
    return to_document_out(session, doc)


@router.patch("/documents/{document_id}", response_model=DocumentOut)
def update_document(document_id: uuid.UUID, payload: DocumentUpdate, session: Session = Depends(get_session)):
    doc = session.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Documento não encontrado.")

    data = payload.model_dump(exclude_unset=True)

    if "category_id" in data and data["category_id"] is not None:
        if not session.get(Category, data["category_id"]):
            raise HTTPException(422, "Categoria inexistente.")
    if "subcategory_id" in data and data["subcategory_id"] is not None:
        sub = session.get(Subcategory, data["subcategory_id"])
        if not sub:
            raise HTTPException(422, "Subcategoria inexistente.")
        eff_cat = data.get("category_id", doc.category_id)
        if eff_cat is not None and sub.category_id != eff_cat:
            raise HTTPException(422, "Subcategoria não pertence à categoria informada.")

    # trocar categoria sem informar subcategoria zera a subcategoria (evita par inconsistente)
    if "category_id" in data and "subcategory_id" not in data:
        doc.subcategory_id = None

    for field, value in data.items():
        setattr(doc, field, value)
    if data:
        doc.classification_source = "user"  # override do usuário (ADR-0007)
    session.commit()
    session.refresh(doc)
    return to_document_out(session, doc)
