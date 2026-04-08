# backend/app/schemas/sales.py
from __future__ import annotations
from datetime import date, datetime
from typing import List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator


class SaleItem(BaseModel):
	"""Sale line item - supports frontend format (qty) and canonical format (quantity)"""
	model_config = ConfigDict(populate_by_name=True)

	recipeId: str
	quantity: float = Field(default=0, ge=0)
	price: Optional[float] = Field(default=None, description="Price per unit (optional, can be calculated from recipe)")
	discountPct: Optional[float] = Field(default=0.0, ge=0, le=100, description="Discount percentage (0-100)")
	markupPct: Optional[float] = Field(default=0.0, ge=0, le=100, description="Markup percentage (0-100)")

	@model_validator(mode="before")
	@classmethod
	def handle_qty_alias(cls, data: Any) -> Any:
		"""Map 'qty' to 'quantity' for frontend compatibility"""
		if isinstance(data, dict):
			if "qty" in data and "quantity" not in data:
				data["quantity"] = data.pop("qty")
		return data


class SaleCreate(BaseModel):
	"""Create sale - supports frontend 'lines' array"""
	model_config = ConfigDict(populate_by_name=True)

	date: date
	items: List[SaleItem] = Field(default_factory=list)
	revenue: Optional[float] = Field(None, description="Total revenue (minor units)")
	notes: Optional[str] = None

	@model_validator(mode="before")
	@classmethod
	def handle_lines_alias(cls, data: Any) -> Any:
		"""Map 'lines' to 'items' for frontend compatibility"""
		if isinstance(data, dict):
			if "lines" in data and "items" not in data:
				data["items"] = data.pop("lines")
		return data


class SaleFull(BaseModel):
	"""Full sale data including restaurantId"""
	model_config = ConfigDict(populate_by_name=True)

	date: date
	items: List[SaleItem] = []
	lines: Optional[List[SaleItem]] = Field(default=None, description="Alias for items (frontend)")
	restaurantId: str
	revenue: Optional[float] = None
	notes: Optional[str] = None

	@model_validator(mode="before")
	@classmethod
	def sync_lines_items(cls, data: Any) -> Any:
		"""Sync lines and items bidirectionally"""
		if isinstance(data, dict):
			# Ensure lines mirrors items for frontend
			if "items" in data and "lines" not in data:
				data["lines"] = data["items"]
			elif "lines" in data and "items" not in data:
				data["items"] = data["lines"]
		return data


class Sale(SaleFull):
	id: str
	createdAt: datetime
