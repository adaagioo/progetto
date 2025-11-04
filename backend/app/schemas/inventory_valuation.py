# backend/app/schemas/inventory_valuation.py
from __future__ import annotations
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel


class ValuationSummaryResponse(BaseModel):
	asOf: date
	total: float
	food: float
	beverage: float
	other: float


class ValuationTotalResponse(BaseModel):
	total: float


class ValuationByCategoryItem(BaseModel):
	category: str
	total: float


class ValuationByCategoryResponse(BaseModel):
	items: List[ValuationByCategoryItem]


class ExpiringItem(BaseModel):
	id: str
	name: str
	expiryDate: datetime
	daysLeft: int


class AdjustmentItem(BaseModel):
	inventoryId: str
	delta: float
	reason: str


class AdjustmentRequest(BaseModel):
	items: List[AdjustmentItem]


class AdjustmentResult(BaseModel):
	ok: bool
	processed: int
	failed: int


class DependenciesResponse(BaseModel):
	inventoryId: str
	recipesUsing: int
	preparationsUsing: int
	recipeIds: List[str] = []
	preparationIds: List[str] = []
