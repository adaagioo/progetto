# backend/app/schemas/dependencies.py
from __future__ import annotations
from typing import List
from pydantic import BaseModel


class PreparationDependencies(BaseModel):
	preparationId: str
	recipesUsing: int
	recipeIds: List[str] = []


class RecipeDependencies(BaseModel):
	recipeId: str
	usedInMenus: int = 0
	usedInPrepList: int = 0
	usedInOrderList: int = 0
	preparationRefs: int = 0
	preparationIds: List[str] = []
