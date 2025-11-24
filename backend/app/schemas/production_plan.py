# backend/app/schemas/production_plan.py
from __future__ import annotations
from datetime import date
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ProductionPlanItem(BaseModel):
	"""Single item in a production plan"""
	recipeId: str
	quantity: float = Field(ge=0, description="Number of portions to prepare")
	source: str = Field(default="manual", description="How this item was added: manual, forecast, reservation")
	notes: Optional[str] = None


class ProductionPlanCreate(BaseModel):
	"""Create a new production plan"""
	date: date
	items: List[ProductionPlanItem] = []
	status: str = Field(default="draft", description="Status: draft, confirmed, completed")
	notes: Optional[str] = None
	basedOnForecast: Optional[Dict[str, Any]] = None


class ProductionPlanUpdate(BaseModel):
	"""Update an existing production plan"""
	items: Optional[List[ProductionPlanItem]] = None
	status: Optional[str] = None
	notes: Optional[str] = None


class ProductionPlan(BaseModel):
	"""Full production plan with metadata"""
	id: str
	restaurantId: str
	date: str  # ISO format date string
	items: List[ProductionPlanItem]
	status: str
	notes: Optional[str] = None
	basedOnForecast: Optional[Dict[str, Any]] = None
	createdAt: str
	updatedAt: Optional[str] = None
