# backend/app/schemas/inventory.py
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class InventoryCreate(BaseModel):
	ingredientId: str
	qty: float = Field(..., ge=0)
	unit: Optional[str] = None
	countType: Optional[str] = None  # opening, closing, adjustment, receiving
	batchExpiry: Optional[str] = None
	location: Optional[str] = None
	unitCost: Optional[float] = None
	receivingId: Optional[str] = None
	restaurantId: Optional[str] = None  # Made optional, will be set by backend


class Inventory(BaseModel):
	id: str
	ingredientId: str
	qty: float
	unit: Optional[str] = None
	countType: Optional[str] = None
	batchExpiry: Optional[str] = None
	location: Optional[str] = None
	unitCost: Optional[float] = None
	receivingId: Optional[str] = None
	restaurantId: str
	createdAt: Optional[str] = None


class InventoryItemBase(BaseModel):
	name: str
	quantity: float
	unit: str | None = None
	reorderLevel: float | None = None
	targetLevel: float | None = None
	defaultSupplierId: str | None = None
