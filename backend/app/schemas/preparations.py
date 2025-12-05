# backend/app/schemas/preparations.py
from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field

class PreparationItem(BaseModel):
    type: str  # 'ingredient' or 'preparation'
    itemId: str
    qty: float = Field(..., ge=0)

class PreparationCreate(BaseModel):
    name: str = Field(..., min_length=1)
    restaurantId: str
    portions: int = Field(1, ge=1)
    items: List[PreparationItem] = Field(default_factory=list)
    notes: Optional[str] = None

class PreparationUpdate(BaseModel):
    name: Optional[str] = None
    portions: Optional[int] = Field(None, ge=1)
    items: Optional[List[PreparationItem]] = None
    notes: Optional[str] = None

class Preparation(BaseModel):
    id: str
    name: str
    restaurantId: str
    portions: int
    items: List[PreparationItem] = []
    notes: Optional[str] = None
    cost: Optional[float] = Field(None, description="Total cost for all portions")
    costPerPortion: Optional[float] = Field(None, description="Cost per single portion")
