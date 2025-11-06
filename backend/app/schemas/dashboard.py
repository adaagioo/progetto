# backend/app/schemas/dashboard.py
from __future__ import annotations
from pydantic import BaseModel


class KPIResponse(BaseModel):
	totalRecipes: int
	totalIngredients: int
	totalInventoryItems: int
	totalSuppliers: int
	totalSalesOrders: int
