# backend/app/schemas/inventory_valuation.py
from __future__ import annotations
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_serializer


class ValuationCategories(BaseModel):
	"""Inventory valuation by category"""
	food: float = Field(default=0.0, description="Food items valuation")
	beverage: float = Field(default=0.0, description="Beverage items valuation")
	supplies: float = Field(default=0.0, description="Non-food supplies valuation (packaging, cleaning, etc.)")


class ValuationSummaryResponse(BaseModel):
	asOf: date
	total: float
	categories: ValuationCategories
	itemCount: int = 0

	@field_serializer('asOf')
	def serialize_as_of(self, value: date) -> str:
		return value.isoformat()


class ValuationTotalResponse(BaseModel):
	total: float = Field(default=0.0, serialization_alias="totalValue")
	totalValue: float = Field(default=0.0, description="Alias for total - frontend compatibility")
	negativeCount: int = Field(default=0, description="Count of items with negative stock")


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
