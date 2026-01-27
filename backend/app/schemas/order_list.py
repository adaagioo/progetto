# backend/app/schemas/order_list.py
from __future__ import annotations
from datetime import date as DateType, timedelta
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator


class OrderItem(BaseModel):
	"""Item that needs to be ordered from supplier"""
	model_config = ConfigDict(json_schema_extra={
		"example": {
			"inventoryId": "507f1f77bcf86cd799439011",
			"name": "Fresh Basil",
			"quantity": 2.5,
			"unit": "kg",
			"supplierId": "507f191e810c19729de860ea"
		}
	}, populate_by_name=True)

	inventoryId: str = Field(..., description="Ingredient/inventory item ID")
	ingredientId: Optional[str] = Field(default=None, description="Alias for inventoryId (frontend)")
	name: str = Field(..., description="Item name")
	ingredientName: Optional[str] = Field(default=None, description="Alias for name (frontend)")
	quantity: float = Field(default=0, description="Quantity to order")
	suggestedQty: Optional[float] = Field(default=None, description="Suggested order quantity (frontend)")
	unit: str | None = Field(None, description="Unit of measurement (kg, L, piece, etc.)")
	supplierId: str | None = Field(None, description="Default supplier ID")
	supplierName: Optional[str] = Field(default=None, description="Supplier name for display")
	# Frontend expected fields
	currentQty: Optional[float] = Field(default=None, description="Current stock quantity")
	minStockQty: Optional[float] = Field(default=None, description="Minimum stock level")
	currentStock: Optional[float] = Field(default=None, description="Alias for currentQty")
	reorderLevel: Optional[float] = Field(default=None, description="Alias for minStockQty")
	targetLevel: Optional[float] = Field(default=None, description="Target stock level")
	plannedConsumption: Optional[float] = Field(default=None, description="Planned consumption")
	projectedStock: Optional[float] = Field(default=None, description="Projected stock after consumption")
	drivers: Optional[List[str]] = Field(default=None, description="Order drivers (low_stock, expiring_soon, etc.)")
	packSize: Optional[float] = Field(default=None, description="Pack size for ordering")
	expiryDate: Optional[str] = Field(default=None, description="Earliest expiry date")
	actualQty: Optional[float] = Field(default=None, description="Actual ordered quantity")
	notes: Optional[str] = Field(default=None, description="Notes")

	@model_validator(mode="before")
	@classmethod
	def sync_alias_fields(cls, data: dict) -> dict:
		"""Ensure alias fields are populated from main fields"""
		if isinstance(data, dict):
			# Sync ingredientId <-> inventoryId
			if not data.get("ingredientId") and data.get("inventoryId"):
				data["ingredientId"] = data["inventoryId"]
			elif not data.get("inventoryId") and data.get("ingredientId"):
				data["inventoryId"] = data["ingredientId"]
			# Sync ingredientName <-> name
			if not data.get("ingredientName") and data.get("name"):
				data["ingredientName"] = data["name"]
			elif not data.get("name") and data.get("ingredientName"):
				data["name"] = data["ingredientName"]
			# Sync suggestedQty <-> quantity
			if data.get("suggestedQty") is None and data.get("quantity") is not None:
				data["suggestedQty"] = data["quantity"]
			# Sync currentQty <-> currentStock
			if data.get("currentQty") is None and data.get("currentStock") is not None:
				data["currentQty"] = data["currentStock"]
			elif data.get("currentStock") is None and data.get("currentQty") is not None:
				data["currentStock"] = data["currentQty"]
			# Sync minStockQty <-> reorderLevel
			if data.get("minStockQty") is None and data.get("reorderLevel") is not None:
				data["minStockQty"] = data["reorderLevel"]
			elif data.get("reorderLevel") is None and data.get("minStockQty") is not None:
				data["reorderLevel"] = data["minStockQty"]
		return data


class OrderListResponse(BaseModel):
	"""Order list for a specific date"""
	model_config = ConfigDict(json_schema_extra={
		"example": {
			"date": "2025-01-21",
			"items": [
				{
					"inventoryId": "507f1f77bcf86cd799439011",
					"name": "Fresh Basil",
					"quantity": 2.5,
					"unit": "kg",
					"supplierId": "507f191e810c19729de860ea"
				}
			]
		}
	})

	date: DateType = Field(..., description="Date for this order list")
	items: List[OrderItem] = Field(..., description="Items that need ordering")


class OrderForecastItem(BaseModel):
	"""Forecast item showing order volume for one day"""
	model_config = ConfigDict(json_schema_extra={
		"example": {
			"date": "2025-01-20",
			"itemsCount": 5
		}
	})

	date: DateType = Field(..., description="Forecast date")
	itemsCount: int = Field(..., description="Number of items to order", ge=0)


class OrderForecastResponse(BaseModel):
	"""Multi-day order forecast"""
	model_config = ConfigDict(json_schema_extra={
		"example": {
			"items": [
				{"date": "2025-01-20", "itemsCount": 5},
				{"date": "2025-01-21", "itemsCount": 3},
				{"date": "2025-01-22", "itemsCount": 7}
			]
		}
	})

	items: List[OrderForecastItem] = Field(..., description="Forecast for each day")
