# backend/app/schemas/suppliers.py
from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, EmailStr


class SupplierCreate(BaseModel):
	name: str
	email: Optional[EmailStr] = None
	phone: Optional[str] = None


class SupplierUpdate(BaseModel):
	name: Optional[str] = None
	email: Optional[EmailStr] = None
	phone: Optional[str] = None


class Supplier(BaseModel):
	id: str
	name: str
	email: Optional[EmailStr] = None
	phone: Optional[str] = None
