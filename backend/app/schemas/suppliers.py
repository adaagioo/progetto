# backend/app/schemas/suppliers.py
from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field

from backend.app.schemas.files import FileRef


class SupplierBase(BaseModel):
	name: str = Field(..., min_length=1)
	email: Optional[str] = None
	phone: Optional[str] = None
	address: Optional[str] = None
	notes: Optional[str] = None
	active: bool = True


class SupplierCreate(SupplierBase):
	pass


class SupplierUpdate(BaseModel):
	name: Optional[str] = None
	email: Optional[str] = None
	phone: Optional[str] = None
	address: Optional[str] = None
	notes: Optional[str] = None
	active: Optional[bool] = None


class Supplier(BaseModel):
	id: str
	name: str
	email: Optional[str] = None
	phone: Optional[str] = None
	address: Optional[str] = None
	notes: Optional[str] = None
	active: bool = True
	files: Optional[List[FileRef]] = None


class SupplierDependencies(BaseModel):
	supplierId: str
	hasReferences: bool
	references: dict  # {"inventoryDefaults": int, "receiving": int}
