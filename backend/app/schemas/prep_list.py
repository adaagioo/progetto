# backend/app/schemas/prep_list.py
from __future__ import annotations
from datetime import date
from typing import List, Optional
from pydantic import BaseModel


class PrepTask(BaseModel):
	preparationId: str
	recipeId: Optional[str] = None
	name: str
	quantity: float
	unit: str | None = None


class PrepListResponse(BaseModel):
	date: date
	tasks: List[PrepTask]


class PrepForecastItem(BaseModel):
	date: date
	tasksCount: int


class PrepForecastResponse(BaseModel):
	items: List[PrepForecastItem]
