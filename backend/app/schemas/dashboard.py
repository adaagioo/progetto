# backend/app/schemas/dashboard.py
from __future__ import annotations
from typing import Optional, Dict
from pydantic import BaseModel, Field


class DateRange(BaseModel):
	start: str = Field(..., description="Start date (ISO format)")
	end: str = Field(..., description="End date (ISO format)")


class KPIResponse(BaseModel):
	totalRecipes: int = Field(..., description="Total number of recipes")
	totalIngredients: int = Field(..., description="Total number of ingredients")
	totalInventoryItems: int = Field(..., description="Total number of inventory items")
	totalSuppliers: int = Field(..., description="Total number of suppliers")
	totalSalesOrders: int = Field(..., description="Total number of sales orders")
	totalSales: Optional[float] = Field(None, description="Total sales revenue for the period")
	valueUsage: Optional[float] = Field(None, description="Total value usage (purchases + wastage) for the period")
	foodCostPct: Optional[float] = Field(None, description="Food cost percentage (value usage / total sales * 100)")
	dateRange: Optional[DateRange] = Field(None, description="Date range for calculations")
