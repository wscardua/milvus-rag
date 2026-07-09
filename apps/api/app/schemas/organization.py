"""Schemas do contrato organization-admin (ADR-0007)."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class SquadCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None


class SquadUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None


class SquadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    description: str | None = None
    process_count: int | None = None
    document_count: int | None = None


class DeliveryProcessCreate(BaseModel):
    squad_id: uuid.UUID
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None


class DeliveryProcessUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None


class DeliveryProcessOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    squad_id: uuid.UUID
    name: str
    description: str | None = None
    document_count: int | None = None


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str


class SubcategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    category_id: uuid.UUID
    name: str
