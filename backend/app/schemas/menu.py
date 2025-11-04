# backend/app/schemas/menu.py
from __future__ import annotations
from datetime import date
from typing import List, Optional
from pydantic import BaseModel


class MenuItem(BaseModel):
	recipeId: str
	quantity: float


class MenuCreate(BaseModel):
	date: date
	items: List[MenuItem]


class MenuUpdate(BaseModel):
	items: List[MenuItem]


class Menu(BaseModel):
	id: str
	date: date
	items: List[MenuItem]
