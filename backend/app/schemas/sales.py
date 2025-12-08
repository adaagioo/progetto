# backend/app/schemas/sales.py
from __future__ import annotations
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class SaleItem(BaseModel):
	recipeId: str
	quantity: float
	price: float
	discountPct: Optional[float] = Field(default=0.0, ge=0, le=100, description="Discount percentage (0-100)")
	markupPct: Optional[float] = Field(default=0.0, ge=0, le=100, description="Markup percentage (0-100)")


class SaleCreate(BaseModel):
	date: date
	items: List[SaleItem]


class SaleFull(BaseModel):
	"""Full sale data including restaurantId"""
	date: date
	items: List[SaleItem]
	restaurantId: str


class Sale(SaleFull):
	id: str
	createdAt: datetime
