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
	# Additional fields for frontend compatibility
	lowStockCount: int = Field(default=0, description="Number of items below minimum stock level")
	expiring1Day: int = Field(default=0, description="Items expiring within 1 day")
	expiring2Day: int = Field(default=0, description="Items expiring within 2 days")
	expiring3Day: int = Field(default=0, description="Items expiring within 3 days")
	lastMonthGrossMargin: Optional[float] = Field(None, description="Gross margin for last month")
	totalRevenue: Optional[float] = Field(None, description="Total revenue (alias for totalSales)")
	totalCogs: Optional[float] = Field(None, description="Total cost of goods sold (alias for valueUsage)")
