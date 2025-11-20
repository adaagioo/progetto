# backend/app/schemas/prep_list.py
from __future__ import annotations
from datetime import date
from typing import List, Optional
from pydantic import BaseModel


class PrepTask(BaseModel):
	preparationId: Optional[str] = None  # Can be None when grouped by ingredient name
	recipeId: Optional[str] = None
	name: str
	preparationName: Optional[str] = None  # Frontend expects this field
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
