# backend/app/schemas/order_list.py
from __future__ import annotations
from datetime import date, timedelta
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


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
	})

	inventoryId: str = Field(..., description="Ingredient/inventory item ID")
	name: str = Field(..., description="Item name")
	quantity: float = Field(..., description="Quantity to order", gt=0)
	unit: str | None = Field(None, description="Unit of measurement (kg, L, piece, etc.)")
	supplierId: str | None = Field(None, description="Default supplier ID")


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

	date: date = Field(..., description="Date for this order list")
	items: List[OrderItem] = Field(..., description="Items that need ordering")


class OrderForecastItem(BaseModel):
	"""Forecast item showing order volume for one day"""
	model_config = ConfigDict(json_schema_extra={
		"example": {
			"date": "2025-01-20",
			"itemsCount": 5
		}
	})

	date: date = Field(..., description="Forecast date")
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
