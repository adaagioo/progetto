# backend/app/schemas/recipes.py
from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field

class RecipeItem(BaseModel):
    type: str  # 'ingredient' or 'preparation'
    itemId: str
    qtyPerPortion: float = Field(..., ge=0)

class RecipeCreate(BaseModel):
    name: str = Field(..., min_length=1)
    restaurantId: str
    portions: int = Field(1, ge=1)
    items: List[RecipeItem] = Field(default_factory=list)
    notes: Optional[str] = None

class RecipeUpdate(BaseModel):
    name: Optional[str] = None
    portions: Optional[int] = Field(None, ge=1)
    items: Optional[List[RecipeItem]] = None
    notes: Optional[str] = None

class Recipe(BaseModel):
    id: str
    name: str
    restaurantId: str
    portions: int
    items: List[RecipeItem] = []
    notes: Optional[str] = None
