"""Modelo de dados da POC (ADR-0003/0007/0008/0009).

Organização:  squad -< delivery_process -< document -< chunk
Taxonomia:    category -< subcategory (tabelas de referência — ADR-0007)
Vínculos:     document_link (auto-relação tipada, mesma squad — ADR-0008)
Fila:         ingestion_job (estado + retry/visibility timeout — ADR-0009)
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# Listas fixas (ver docs/specs/reference/taxonomy.md e ADR-0008/0009)
LINK_TYPES = ("esclarece", "complementa", "precede", "substitui")
JOB_STATES = ("pending", "processing", "indexed", "failed")
CLASSIFICATION_SOURCES = ("llm", "user")
DOC_TYPES = (
    "Documento técnico", "Manual / Guia", "Procedimento / Runbook", "Especificação / Requisito",
    "Ata / Registro de reunião", "Transcrição de reunião", "Base de Conhecimento",
    "Apresentação", "Planilha", "Contrato / Documento legal", "Código-fonte", "Relatório", "Outro",
)
# Extensões aceitas no upload (ADR-0002)
ALLOWED_EXTENSIONS = (".pdf", ".docx", ".txt", ".md", ".html", ".htm", ".py", ".xls", ".xlsx")


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Squad(TimestampMixin, Base):
    __tablename__ = "squad"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    processes: Mapped[list["DeliveryProcess"]] = relationship(back_populates="squad")


class DeliveryProcess(TimestampMixin, Base):
    __tablename__ = "delivery_process"
    __table_args__ = (UniqueConstraint("squad_id", "name", name="uq_process_squad_name"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    squad_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("squad.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    squad: Mapped["Squad"] = relationship(back_populates="processes")
    documents: Mapped[list["Document"]] = relationship(back_populates="delivery_process")


class Category(Base):
    __tablename__ = "category"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)

    subcategories: Mapped[list["Subcategory"]] = relationship(back_populates="category")


class Subcategory(Base):
    __tablename__ = "subcategory"
    __table_args__ = (UniqueConstraint("category_id", "name", name="uq_subcat_category_name"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("category.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)

    category: Mapped["Category"] = relationship(back_populates="subcategories")


class Document(TimestampMixin, Base):
    __tablename__ = "document"

    id: Mapped[uuid.UUID] = _uuid_pk()
    delivery_process_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("delivery_process.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    # Metadados do usuário
    title: Mapped[str | None] = mapped_column(String(500))  # opcional (IA sugere) — ADR-0007
    author: Mapped[str | None] = mapped_column(String(200))
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), server_default="{}", nullable=False)
    doc_type: Mapped[str | None] = mapped_column(String(120))

    # Arquivo
    original_filename: Mapped[str | None] = mapped_column(String(500))
    mime_type: Mapped[str | None] = mapped_column(String(200))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    storage_path: Mapped[str | None] = mapped_column(Text)

    # Classificação sugerida por IA e editável (ADR-0007)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("category.id", ondelete="SET NULL"), index=True
    )
    subcategory_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("subcategory.id", ondelete="SET NULL")
    )
    summary: Mapped[str | None] = mapped_column(Text)
    classification_source: Mapped[str | None] = mapped_column(String(10))
    ingested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "classification_source IS NULL OR classification_source IN ('llm','user')",
            name="ck_document_classification_source",
        ),
    )

    delivery_process: Mapped["DeliveryProcess"] = relationship(back_populates="documents")
    category: Mapped["Category | None"] = relationship()
    subcategory: Mapped["Subcategory | None"] = relationship()
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    ingestion_jobs: Mapped[list["IngestionJob"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class DocumentLink(Base):
    """Vínculo direcionado e tipado entre documentos (mesma squad — ADR-0008).

    A restrição de mesma squad é validada na API (envolve join squad↔processo).
    """
    __tablename__ = "document_link"
    __table_args__ = (
        UniqueConstraint("source_document_id", "target_document_id", "link_type", name="uq_link"),
        CheckConstraint("source_document_id <> target_document_id", name="ck_link_no_self"),
        CheckConstraint(
            "link_type IN ('esclarece','complementa','precede','substitui')",
            name="ck_link_type",
        ),
        Index("ix_link_source", "source_document_id"),
        Index("ix_link_target", "target_document_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    source_document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document.id", ondelete="CASCADE"), nullable=False
    )
    target_document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document.id", ondelete="CASCADE"), nullable=False
    )
    link_type: Mapped[str] = mapped_column(String(20), nullable=False)
    ordinal: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Chunk(Base):
    __tablename__ = "chunk"
    __table_args__ = (
        UniqueConstraint("document_id", "ordinal", name="uq_chunk_doc_ordinal"),
        Index("ix_chunk_document", "document_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document.id", ondelete="CASCADE"), nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    milvus_vector_id: Mapped[str | None] = mapped_column(String(64))
    token_count: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    document: Mapped["Document"] = relationship(back_populates="chunks")


class IngestionJob(TimestampMixin, Base):
    """Fila de ingestão + retry/visibility timeout (ADR-0004 / ADR-0009)."""
    __tablename__ = "ingestion_job"
    __table_args__ = (
        CheckConstraint(
            "state IN ('pending','processing','indexed','failed')", name="ck_job_state"
        ),
        Index("ix_job_claim", "state", "available_at"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document.id", ondelete="CASCADE"), nullable=False, index=True
    )
    state: Mapped[str] = mapped_column(String(20), server_default="pending", nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    document: Mapped["Document"] = relationship(back_populates="ingestion_jobs")
