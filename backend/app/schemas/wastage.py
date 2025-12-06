# backend/app/schemas/wastage.py
from __future__ import annotations
from datetime import date, datetime
from typing import List
from pydantic import BaseModel


class WastageItem(BaseModel):
	inventoryId: str
	quantity: float
	reason: str


class WastageCreate(BaseModel):
	date: date
	items: List[WastageItem]


class WastageFull(BaseModel):
	"""Full wastage data including restaurantId"""
	date: date
	items: List[WastageItem]
	restaurantId: str


class Wastage(WastageFull):
	id: str
	createdAt: datetime
