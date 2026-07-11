"""Contrato upload-and-metadata (ADR-0007): upload, listagem, detalhe e overrides."""
from __future__ import annotations

import json
import os
import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.links import create_document_link
from app.api.serializers import to_document_out
from app.config import settings
from app.db.base import get_session
from app.db.models import (
    ALLOWED_EXTENSIONS,
    DELIVERY_PHASES,
    DOC_TYPES,
    Category,
    DeliveryProcess,
    Document,
    IngestionJob,
    Subcategory,
)
from app.schemas.document import DocumentOut, DocumentUpdate, LinkIn
from app.services import eventlog, storage, vectorstore

router = APIRouter(tags=["documents"])


@router.post("/documents", response_model=DocumentOut, status_code=201)
def upload_document(
    file: UploadFile = File(...),
    delivery_process_id: uuid.UUID = Form(...),
    title: str | None = Form(None),
    author: str | None = Form(None),
    doc_type: str = Form(...),  # obrigatório (ADR-0013): orienta o perfil de chunking na ingestão
    delivery_phase: str | None = Form(None),  # opcional (ADR-0014): fase do ciclo de entrega
    valid_until: date | None = Form(None),  # opcional (ADR-0014): data ISO; após ela → rebaixado no retrieval
    tags: str | None = Form(None),  # separadas por vírgula
    links: str | None = Form(None),  # JSON: [{"target_document_id","link_type","ordinal"}]
    session: Session = Depends(get_session),
):
    process = session.get(DeliveryProcess, delivery_process_id)
    if not process:
        raise HTTPException(422, "Processo de delivery inexistente.")

    if doc_type not in DOC_TYPES:
        raise HTTPException(422, f"doc_type inválido. Use um de {DOC_TYPES}.")

    if delivery_phase is not None and delivery_phase not in DELIVERY_PHASES:
        raise HTTPException(422, f"delivery_phase inválida. Use uma de {DELIVERY_PHASES}.")

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
        delivery_phase=delivery_phase,
        valid_until=valid_until,
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
    response: Response,
    squad_id: uuid.UUID | None = None,
    delivery_process_id: uuid.UUID | None = None,
    delivery_phase: str | None = None,  # ADR-0014 (filtro no Postgres, não no Milvus)
    category_id: uuid.UUID | None = None,
    doc_type: str | None = None,
    tags: list[str] | None = Query(None),  # ADR-0015 — OR (overlap), mesma semântica do Milvus
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_session),
):
    stmt = select(Document)
    if squad_id:
        stmt = stmt.join(DeliveryProcess, Document.delivery_process_id == DeliveryProcess.id).where(
            DeliveryProcess.squad_id == squad_id
        )
    if delivery_process_id:
        stmt = stmt.where(Document.delivery_process_id == delivery_process_id)
    if delivery_phase:
        stmt = stmt.where(Document.delivery_phase == delivery_phase)
    if category_id:
        stmt = stmt.where(Document.category_id == category_id)
    if doc_type:
        stmt = stmt.where(Document.doc_type == doc_type)
    if tags:
        # overlap (&&) usa o índice GIN existente (ADR-0007) — hit com qualquer uma das tags pedidas
        stmt = stmt.where(Document.tags.overlap(tags))

    # Total do recorte (sem paginação) → X-Total-Count para a UI paginar (contrato upload-and-metadata)
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    response.headers["X-Total-Count"] = str(total)

    docs = session.scalars(
        stmt.order_by(Document.created_at.desc()).limit(min(limit, 200)).offset(offset)
    ).all()
    return [to_document_out(session, d) for d in docs]


@router.get("/tags", response_model=list[str])
def list_tags(session: Session = Depends(get_session)):
    """Tags distintas já usadas no acervo (ADR-0015) — popula dropdown/tool (`list_tags` no MCP)."""
    stmt = select(func.unnest(Document.tags)).distinct()
    return sorted(session.execute(stmt).scalars().all())


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
    if data.get("delivery_phase") is not None and data["delivery_phase"] not in DELIVERY_PHASES:
        raise HTTPException(422, f"delivery_phase inválida. Use uma de {DELIVERY_PHASES}.")

    # trocar categoria sem informar subcategoria zera a subcategoria (evita par inconsistente)
    if "category_id" in data and "subcategory_id" not in data:
        doc.subcategory_id = None

    if "tags" in data:
        data["tags"] = [t.strip() for t in (data["tags"] or []) if t and t.strip()]

    # Campos editados aqui que também vivem no payload do Milvus (ADR-0007/0015) precisam
    # ser resincronizados nos chunks já indexados — o PATCH só grava no Postgres por padrão
    # e o payload do índice ficaria obsoleto sem isso. `category_id` é campo declarado (nunca
    # pode ficar ausente da linha → "" quando limpo); `delivery_phase`/`tags` são campos
    # dinâmicos (`None` remove o campo). `title`/`subcategory_id`/`summary`/`valid_until` não
    # estão no payload do Milvus — nada a sincronizar para eles.
    milvus_fields: dict = {}
    if "category_id" in data:
        milvus_fields["category_id"] = str(data["category_id"]) if data["category_id"] else ""
    if "delivery_phase" in data:
        milvus_fields["delivery_phase"] = data["delivery_phase"] or None
    if "tags" in data:
        milvus_fields["tags"] = vectorstore.serialize_tags(data["tags"]) if data["tags"] else None

    for field, value in data.items():
        setattr(doc, field, value)
    # Override de classificação (ADR-0007) marca classification_source=user; editar só
    # delivery_phase/valid_until/tags (entrada do usuário — ADR-0007/0014) NÃO altera
    # classification_source.
    if data.keys() & {"title", "category_id", "subcategory_id", "summary"}:
        doc.classification_source = "user"

    # Milvus antes do Postgres (mesma ordem de segurança do DELETE, ADR-0010): se a
    # sincronização falhar, o PATCH falha inteiro em vez de deixar Postgres/Milvus divergentes.
    if milvus_fields:
        vectorstore.sync_document_fields(str(doc.id), milvus_fields)

    session.commit()
    session.refresh(doc)
    return to_document_out(session, doc)


@router.get("/documents/{document_id}/file")
def get_document_file(
    document_id: uuid.UUID,
    download: bool = False,
    session: Session = Depends(get_session),
):
    """Serve o arquivo original para visualização (inline) ou download (attachment).

    Fonte da verdade do arquivo é a API (ADR-0010): a UI Django faz proxy, nunca lê o disco.
    """
    doc = session.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Documento não encontrado.")
    if not doc.storage_path or not os.path.exists(doc.storage_path):
        raise HTTPException(404, "Arquivo do documento indisponível.")
    # FileResponse cuida da codificação do filename (RFC 5987) p/ nomes acentuados.
    return FileResponse(
        doc.storage_path,
        media_type=doc.mime_type or "application/octet-stream",
        filename=doc.original_filename or str(document_id),
        content_disposition_type="attachment" if download else "inline",
    )


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(document_id: uuid.UUID, session: Session = Depends(get_session)):
    """Exclui o documento e tudo que o rastreia (ADR-0010).

    Ordem: vetores no Milvus → linha no Postgres (cascade em chunk/ingestion_job/
    document_link) → arquivo em disco. `query_log` NÃO é afetado (histórico de avaliação).
    """
    doc = session.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Documento não encontrado.")

    storage_path = doc.storage_path
    original_filename = doc.original_filename

    # 1) vetores no índice (antes do Postgres: se falhar, doc/chunks seguem rastreáveis)
    vectorstore.delete_by_document(str(document_id))
    # 2) Postgres: cascade remove chunk / ingestion_job / document_link
    session.delete(doc)
    session.commit()
    # 3) arquivo físico (best-effort; a fonte de verdade relacional já foi removida)
    storage.delete_file(storage_path)

    eventlog.log_event(
        "INFO", "api", "document_deleted",
        f"Documento {document_id} excluído.",
        document_id=document_id, original_filename=original_filename,
    )
    return None
