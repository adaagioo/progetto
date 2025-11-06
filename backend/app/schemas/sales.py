# backend/app/schemas/sales.py
from __future__ import annotations
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel


class SaleItem(BaseModel):
	recipeId: str
	quantity: float
	price: float


class SaleCreate(BaseModel):
	date: date
	items: List[SaleItem]


class Sale(BaseModel):
	id: str
	date: date
	items: List[SaleItem]
	createdAt: datetime
