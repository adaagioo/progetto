# backend/app/schemas/prep_list.py
from __future__ import annotations
from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator


class PrepTask(BaseModel):
	model_config = ConfigDict(populate_by_name=True)
	preparationId: Optional[str] = None  # Can be None when grouped by ingredient name
	recipeId: Optional[str] = None
	name: str
	preparationName: Optional[str] = None  # Frontend expects this field
	quantity: float = 0
	unit: str | None = None
	# Frontend expected fields
	forecastQty: Optional[float] = Field(default=None, description="Forecasted quantity needed")
	availableQty: Optional[float] = Field(default=0, description="Currently available quantity")
	toMakeQty: Optional[float] = Field(default=None, description="Quantity to make (forecast - available)")
	overrideQty: Optional[float] = Field(default=None, description="Manual override quantity")
	actualQty: Optional[float] = Field(default=None, description="Actual quantity made")
	forecastSource: Optional[str] = Field(default="production_plan", description="Source of forecast")
	notes: Optional[str] = Field(default=None, description="Notes for this task")

	@model_validator(mode="before")
	@classmethod
	def sync_alias_fields(cls, data: dict) -> dict:
		"""Ensure alias fields are populated from main fields"""
		if isinstance(data, dict):
			# Sync preparationName <-> name
			if not data.get("preparationName") and data.get("name"):
				data["preparationName"] = data["name"]
			elif not data.get("name") and data.get("preparationName"):
				data["name"] = data["preparationName"]
			# Ensure forecastQty is set from quantity
			if data.get("forecastQty") is None and data.get("quantity") is not None:
				data["forecastQty"] = data["quantity"]
			# Ensure toMakeQty is set (forecastQty - availableQty)
			if data.get("toMakeQty") is None:
				forecast = data.get("forecastQty") or data.get("quantity") or 0
				available = data.get("availableQty") or 0
				data["toMakeQty"] = forecast - available
		return data


class PrepListResponse(BaseModel):
	model_config = ConfigDict(populate_by_name=True)

	date: date
	tasks: List[PrepTask] = Field(default_factory=list)
	items: List[PrepTask] = Field(default_factory=list, description="Alias for tasks (frontend)")


class PrepForecastItem(BaseModel):
	date: date
	tasksCount: int


class PrepForecastResponse(BaseModel):
	items: List[PrepForecastItem]
