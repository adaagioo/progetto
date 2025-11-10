# backend/app/schemas/ingredients.py
from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import date


class IngredientBase(BaseModel):
	name: str = Field(..., min_length=1)
	unit: str = Field(..., description="Unit of measure, e.g., g, kg, ml")
	sku: Optional[str] = None
	allergenCodes: Optional[List[str]] = None
	restaurantId: str


class IngredientCreate(IngredientBase):
	pass


class IngredientUpdate(BaseModel):
	name: Optional[str] = None
	unit: Optional[str] = None
	sku: Optional[str] = None
	allergenCodes: Optional[List[str]] = None


class Ingredient(IngredientBase):
	id: str


# TODO (af): normalization
class PricePoint(BaseModel):
	date: date
	unitCost: float | None = None
	receivingId: str | None = None
