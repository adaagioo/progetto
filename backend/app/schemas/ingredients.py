# backend/app/schemas/ingredients.py
from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import date


class ShelfLife(BaseModel):
	"""Shelf life configuration"""
	defaultDays: Optional[int] = None
	minDays: Optional[int] = None
	maxDays: Optional[int] = None


class IngredientBase(BaseModel):
	name: str = Field(..., min_length=1)
	unit: str = Field(..., description="Unit of measure, e.g., g, kg, ml")
	packSize: float = Field(default=1.0, description="Package size in unit")
	packCost: float = Field(default=0.0, description="Cost per package")
	preferredSupplierId: Optional[str] = None
	allergens: Optional[List[str]] = []
	otherAllergens: Optional[List[str]] = []
	minStockQty: float = Field(default=0.0)
	category: Optional[str] = "food"
	wastePct: Optional[float] = Field(default=0.0, ge=0, le=100)
	shelfLife: Optional[ShelfLife] = None
	sku: Optional[str] = None


class IngredientCreate(IngredientBase):
	"""Create ingredient - restaurantId is added from authenticated user"""
	pass


class IngredientFull(IngredientBase):
	"""Full ingredient data including restaurantId"""
	restaurantId: str


class IngredientUpdate(BaseModel):
	name: Optional[str] = None
	unit: Optional[str] = None
	packSize: Optional[float] = None
	packCost: Optional[float] = None
	preferredSupplierId: Optional[str] = None
	allergens: Optional[List[str]] = None
	otherAllergens: Optional[List[str]] = None
	minStockQty: Optional[float] = None
	category: Optional[str] = None
	wastePct: Optional[float] = None
	shelfLife: Optional[ShelfLife] = None
	sku: Optional[str] = None


class Ingredient(IngredientFull):
	model_config = ConfigDict(extra="ignore")
	id: str
	unitCost: Optional[float] = None
	effectiveUnitCost: Optional[float] = None
	preferredSupplierName: Optional[str] = None
	lastPrice: Optional[float] = None
	createdAt: Optional[str] = None


class PricePoint(BaseModel):
	date: date
	unitCost: float | None = None
	receivingId: str | None = None
