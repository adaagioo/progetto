# backend/app/schemas/pl.py
from __future__ import annotations
from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict


class PLResponse(BaseModel):
	start: date
	end: date
	revenue: float
	costOfGoods: float
	wastageCost: float
	grossMargin: float


class PLPeriod(BaseModel):
	"""P&L period definition"""
	start: str  # YYYY-MM-DD
	end: str  # YYYY-MM-DD
	timezone: str = "Europe/Rome"
	granularity: str = "WEEK"  # Weekly Mon-Sun


class PLSnapshotCreate(BaseModel):
	"""Create P&L snapshot"""
	period: PLPeriod
	currency: str
	displayLocale: str
	sales_turnover: float
	sales_food_beverage: float
	sales_delivery: float
	cogs_food_beverage: float
	cogs_raw_waste: float
	opex_non_food: float
	opex_platforms: float
	labour_employees: float
	labour_staff_meal: float
	marketing_online_ads: float
	marketing_free_items: float
	rent_base_effective: float
	rent_garden: float
	other_total: float
	notes: Optional[str] = None


class PLSnapshot(BaseModel):
	"""Complete P&L snapshot"""
	model_config = ConfigDict(extra="ignore")
	id: str
	restaurantId: str
	period: PLPeriod
	currency: str
	displayLocale: str

	# Sales section
	sales_turnover: float
	sales_food_beverage: float
	sales_delivery: float

	# COGS section
	cogs_food_beverage: float
	cogs_raw_waste: float
	cogs_total: float

	# OPEX section
	opex_non_food: float
	opex_platforms: float
	opex_total: float

	# Labour section
	labour_employees: float
	labour_staff_meal: float
	labour_total: float

	# Marketing section
	marketing_online_ads: float
	marketing_free_items: float
	marketing_total: float

	# Rent section
	rent_base_effective: float
	rent_garden: float
	rent_total: float

	# Other costs
	other_total: float

	# KPI
	kpi_ebitda: float

	# Metadata
	notes: Optional[str] = None
	createdAt: str
	updatedAt: Optional[str] = None


class PLCreate(BaseModel):
	"""Create legacy P&L record"""
	month: str
	revenue: float
	cogs: float
	grossMargin: float
	notes: Optional[str] = None


class PL(BaseModel):
	"""Legacy P&L model"""
	model_config = ConfigDict(extra="ignore")
	id: str
	restaurantId: str
	month: str
	revenue: float
	cogs: float
	grossMargin: float
	notes: Optional[str] = None
	createdAt: str
