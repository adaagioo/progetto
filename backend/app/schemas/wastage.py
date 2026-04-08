# backend/app/schemas/wastage.py
from __future__ import annotations
from datetime import date, datetime
from typing import List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator


class WastageItem(BaseModel):
	"""Wastage item - supports both frontend (itemId/qty) and backend (inventoryId/quantity) formats"""
	model_config = ConfigDict(populate_by_name=True)

	inventoryId: Optional[str] = Field(default=None, description="ID of inventory item")
	itemId: Optional[str] = Field(default=None, description="Alias for inventoryId (frontend)")
	ingredientId: Optional[str] = Field(default=None, description="ID of the ingredient")
	ingredientName: Optional[str] = Field(default=None, description="Name of the ingredient")
	itemName: Optional[str] = Field(default=None, description="Name for frontend display")
	quantity: float = Field(default=0, ge=0)
	qty: Optional[float] = Field(default=None, description="Alias for quantity (frontend)")
	reason: Optional[str] = Field(default=None)
	unit: Optional[str] = Field(default=None, description="Unit of measure")
	unitCost: Optional[float] = Field(default=None, description="Unit cost for calculations")

	@model_validator(mode="before")
	@classmethod
	def normalize_fields(cls, data: Any) -> Any:
		"""Map frontend field names to backend field names"""
		if isinstance(data, dict):
			# itemId -> inventoryId
			if "itemId" in data and "inventoryId" not in data:
				data["inventoryId"] = data["itemId"]
			elif "inventoryId" in data and "itemId" not in data:
				data["itemId"] = data["inventoryId"]
			# qty -> quantity
			if "qty" in data and "quantity" not in data:
				data["quantity"] = data["qty"]
			elif "quantity" in data and "qty" not in data:
				data["qty"] = data["quantity"]
		return data


class WastageCreate(BaseModel):
	"""Create wastage - supports both single item and array formats"""
	model_config = ConfigDict(populate_by_name=True)

	date: date
	items: Optional[List[WastageItem]] = Field(default=None)
	# Single-item frontend fields
	type: Optional[str] = Field(default=None, description="Wastage type (e.g., spoilage, damage)")
	itemId: Optional[str] = Field(default=None, description="Single item ID (frontend)")
	qty: Optional[float] = Field(default=None, description="Single item quantity (frontend)")
	unit: Optional[str] = Field(default=None, description="Unit of measure")
	reason: Optional[str] = Field(default=None)
	notes: Optional[str] = Field(default=None)
	unitCost: Optional[float] = Field(default=None, description="Unit cost for calculations")

	@model_validator(mode="before")
	@classmethod
	def normalize_to_items_array(cls, data: Any) -> Any:
		"""Convert single-item format to items array format"""
		if isinstance(data, dict):
			# If items array not provided but single-item fields are, wrap in array
			if "items" not in data and "itemId" in data:
				item = {
					"inventoryId": data.get("itemId"),
					"itemId": data.get("itemId"),
					"quantity": data.get("qty", 0),
					"qty": data.get("qty", 0),
					"reason": data.get("reason"),
					"unit": data.get("unit"),
					"unitCost": data.get("unitCost"),
				}
				data["items"] = [item]
			# Ensure items is a list
			if "items" not in data:
				data["items"] = []
		return data


class WastageFull(BaseModel):
	"""Full wastage data including restaurantId"""
	model_config = ConfigDict(populate_by_name=True)

	date: date
	items: List[WastageItem] = []
	restaurantId: str
	type: Optional[str] = None
	notes: Optional[str] = None


class Wastage(WastageFull):
	id: str
	createdAt: datetime
	# Top-level fields for frontend display (from first item)
	itemName: Optional[str] = None
	qty: Optional[float] = None
	unit: Optional[str] = None
	reason: Optional[str] = None
	costImpact: Optional[float] = None
