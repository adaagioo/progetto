# backend/app/schemas/receiving.py
from __future__ import annotations
from typing import List, Optional
from datetime import date
from pydantic import BaseModel, Field

class ReceivingItem(BaseModel):
    inventoryId: str
    quantity: float = Field(..., ge=0)
    unit: Optional[str] = None
    unitCost: Optional[float] = None
    supplierId: Optional[str] = None
    notes: Optional[str] = None

class ReceivingCreate(BaseModel):
    date: date
    items: List[ReceivingItem]

class Receiving(BaseModel):
    id: str
    date: date
    items: List[ReceivingItem]
    createdAt: str
