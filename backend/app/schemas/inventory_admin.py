# backend/app/schemas/inventory_admin.py
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel


class InventoryBulkPatch(BaseModel):
	inventoryId: str
	reorderLevel: float | None = None
	targetLevel: float | None = None
	unit: str | None = None
	defaultSupplierId: str | None = None
	name: str | None = None


class InventoryBulkUpdateRequest(BaseModel):
	items: List[InventoryBulkPatch]
