# backend/app/schemas/inventory.py
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field

class InventoryCreate(BaseModel):
    ingredientId: str
    qty: float = Field(..., ge=0)
    unitCost: Optional[float] = None
    receivingId: Optional[str] = None
    restaurantId: str

class Inventory(BaseModel):
    id: str
    ingredientId: str
    qty: float
    unitCost: Optional[float] = None
    receivingId: Optional[str] = None
    restaurantId: str
