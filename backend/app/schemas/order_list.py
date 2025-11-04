# backend/app/schemas/order_list.py
from __future__ import annotations
from datetime import date, timedelta
from typing import List, Optional
from pydantic import BaseModel


class OrderItem(BaseModel):
	inventoryId: str
	name: str
	quantity: float
	unit: str | None = None
	supplierId: str | None = None


class OrderListResponse(BaseModel):
	date: date
	items: List[OrderItem]


class OrderForecastItem(BaseModel):
	date: date
	itemsCount: int


class OrderForecastResponse(BaseModel):
	items: List[OrderForecastItem]
