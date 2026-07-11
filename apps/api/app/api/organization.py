"""Contrato organization-admin (ADR-0007): CRUD de squads/processos + leitura de taxonomia."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import get_session
from app.db.models import (
    DELIVERY_PHASES,
    DOC_TYPES,
    LINK_TYPES,
    Category,
    DeliveryProcess,
    Document,
    Squad,
    Subcategory,
)
from app.schemas.organization import (
    CategoryOut,
    DeliveryProcessCreate,
    DeliveryProcessOut,
    DeliveryProcessUpdate,
    SquadCreate,
    SquadOut,
    SquadUpdate,
    SubcategoryOut,
)

router = APIRouter(tags=["organization"])


# ---------- Squads ----------
@router.get("/squads", response_model=list[SquadOut])
def list_squads(session: Session = Depends(get_session)):
    squads = session.scalars(select(Squad).order_by(Squad.name)).all()
    out = []
    for s in squads:
        pc = session.scalar(select(func.count(DeliveryProcess.id)).where(DeliveryProcess.squad_id == s.id))
        dc = session.scalar(
            select(func.count(Document.id))
            .join(DeliveryProcess, Document.delivery_process_id == DeliveryProcess.id)
            .where(DeliveryProcess.squad_id == s.id)
        )
        out.append(SquadOut(id=s.id, name=s.name, description=s.description, process_count=pc, document_count=dc))
    return out


@router.post("/squads", response_model=SquadOut, status_code=201)
def create_squad(payload: SquadCreate, session: Session = Depends(get_session)):
    squad = Squad(name=payload.name, description=payload.description)
    session.add(squad)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "Já existe uma squad com esse nome.")
    session.refresh(squad)
    return SquadOut.model_validate(squad)


@router.patch("/squads/{squad_id}", response_model=SquadOut)
def update_squad(squad_id: uuid.UUID, payload: SquadUpdate, session: Session = Depends(get_session)):
    squad = session.get(Squad, squad_id)
    if not squad:
        raise HTTPException(404, "Squad não encontrada.")
    if payload.name is not None:
        squad.name = payload.name
    if payload.description is not None:
        squad.description = payload.description
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "Já existe uma squad com esse nome.")
    session.refresh(squad)
    return SquadOut.model_validate(squad)


@router.delete("/squads/{squad_id}", status_code=204)
def delete_squad(squad_id: uuid.UUID, session: Session = Depends(get_session)):
    squad = session.get(Squad, squad_id)
    if not squad:
        raise HTTPException(404, "Squad não encontrada.")
    session.delete(squad)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "Squad tem processos/documentos vinculados (RESTRICT).")


# ---------- Processos de delivery ----------
@router.get("/delivery-processes", response_model=list[DeliveryProcessOut])
def list_processes(squad_id: uuid.UUID | None = None, session: Session = Depends(get_session)):
    stmt = select(DeliveryProcess).order_by(DeliveryProcess.name)
    if squad_id:
        stmt = stmt.where(DeliveryProcess.squad_id == squad_id)
    procs = session.scalars(stmt).all()
    out = []
    for p in procs:
        dc = session.scalar(select(func.count(Document.id)).where(Document.delivery_process_id == p.id))
        out.append(
            DeliveryProcessOut(
                id=p.id, squad_id=p.squad_id, name=p.name, description=p.description, document_count=dc
            )
        )
    return out


@router.post("/delivery-processes", response_model=DeliveryProcessOut, status_code=201)
def create_process(payload: DeliveryProcessCreate, session: Session = Depends(get_session)):
    if not session.get(Squad, payload.squad_id):
        raise HTTPException(422, "Squad inexistente.")
    proc = DeliveryProcess(squad_id=payload.squad_id, name=payload.name, description=payload.description)
    session.add(proc)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "Já existe um processo com esse nome nessa squad.")
    session.refresh(proc)
    return DeliveryProcessOut.model_validate(proc)


@router.patch("/delivery-processes/{process_id}", response_model=DeliveryProcessOut)
def update_process(process_id: uuid.UUID, payload: DeliveryProcessUpdate, session: Session = Depends(get_session)):
    proc = session.get(DeliveryProcess, process_id)
    if not proc:
        raise HTTPException(404, "Processo não encontrado.")
    if payload.name is not None:
        proc.name = payload.name
    if payload.description is not None:
        proc.description = payload.description
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "Já existe um processo com esse nome nessa squad.")
    session.refresh(proc)
    return DeliveryProcessOut.model_validate(proc)


@router.delete("/delivery-processes/{process_id}", status_code=204)
def delete_process(process_id: uuid.UUID, session: Session = Depends(get_session)):
    proc = session.get(DeliveryProcess, process_id)
    if not proc:
        raise HTTPException(404, "Processo não encontrado.")
    session.delete(proc)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "Processo tem documentos vinculados (RESTRICT).")


# ---------- Taxonomia (leitura) ----------
@router.get("/doc-types", response_model=list[str])
def list_doc_types():
    return list(DOC_TYPES)


@router.get("/link-types", response_model=list[str])
def list_link_types():
    return list(LINK_TYPES)


@router.get("/delivery-phases", response_model=list[str])
def list_delivery_phases():
    """Lista fechada de fases do ciclo de entrega (ADR-0014)."""
    return list(DELIVERY_PHASES)


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(session: Session = Depends(get_session)):
    return session.scalars(select(Category).order_by(Category.name)).all()


@router.get("/categories/{category_id}/subcategories", response_model=list[SubcategoryOut])
def list_subcategories(category_id: uuid.UUID, session: Session = Depends(get_session)):
    if not session.get(Category, category_id):
        raise HTTPException(404, "Categoria não encontrada.")
    return session.scalars(
        select(Subcategory).where(Subcategory.category_id == category_id).order_by(Subcategory.name)
    ).all()
