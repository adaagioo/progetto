# backend/app/api/V1/production_plan.py
from __future__ import annotations
from datetime import date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from backend.app.deps.auth import get_current_user
from backend.app.core.rbac_policies import get_resource_access
from backend.app.schemas.production_plan import (
	ProductionPlan,
	ProductionPlanCreate,
	ProductionPlanUpdate,
)
from backend.app.repositories import production_plan_repo as repo
from backend.app.services.production_plan_service import (
	populate_plan_items_with_recipe_data,
	generate_plan_from_sales_forecast,
	validate_recipe_exists,
)

router = APIRouter()
RESOURCE = "production-plan"


@router.post("/production-plan", response_model=ProductionPlan, status_code=status.HTTP_201_CREATED)
async def create_production_plan(
	payload: ProductionPlanCreate,
	user: dict = Depends(get_current_user)
):
	"""Create a new production plan"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canCreate"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	# Validate all recipes exist
	for item in payload.items:
		if not await validate_recipe_exists(item.recipeId, user["restaurantId"]):
			raise HTTPException(
				status_code=status.HTTP_400_BAD_REQUEST,
				detail=f"Recipe {item.recipeId} not found"
			)

	# Create production plan
	items_data = [item.model_dump() for item in payload.items]
	plan_id = await repo.create_production_plan(
		restaurant_id=user["restaurantId"],
		plan_date=payload.date,
		items=items_data,
		status=payload.status,
		notes=payload.notes,
		based_on_forecast=payload.basedOnForecast
	)

	# Return created plan
	plan = await repo.get_production_plan(plan_id, user["restaurantId"])
	return ProductionPlan(**plan)


@router.get("/production-plan", response_model=List[ProductionPlan])
async def list_production_plans(
	start: Optional[date] = Query(None, description="Start date filter"),
	end: Optional[date] = Query(None, description="End date filter"),
	status: Optional[str] = Query(None, description="Status filter: draft, confirmed, completed"),
	user: dict = Depends(get_current_user)
):
	"""List production plans with optional filters"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	plans = await repo.list_production_plans(
		restaurant_id=user["restaurantId"],
		start_date=start,
		end_date=end,
		status=status
	)

	return [ProductionPlan(**p) for p in plans]


@router.get("/production-plan/{plan_id}", response_model=ProductionPlan)
async def get_production_plan(
	plan_id: str,
	user: dict = Depends(get_current_user)
):
	"""Get a specific production plan"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	plan = await repo.get_production_plan(plan_id, user["restaurantId"])
	if not plan:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production plan not found")

	return ProductionPlan(**plan)


@router.get("/production-plan/by-date/{plan_date}")
async def get_production_plan_by_date(
	plan_date: date,
	user: dict = Depends(get_current_user)
):
	"""Get production plan for a specific date with enriched recipe data"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	plan = await repo.get_production_plan_by_date(user["restaurantId"], plan_date)

	if not plan:
		# Return empty plan structure instead of 404
		return {
			"id": None,
			"restaurantId": user["restaurantId"],
			"date": plan_date.isoformat(),
			"items": [],
			"status": "draft",
			"notes": None,
			"basedOnForecast": None,
			"createdAt": None,
			"updatedAt": None
		}

	# Enrich items with recipe data
	plan["items"] = await populate_plan_items_with_recipe_data(plan["items"])

	return plan


@router.put("/production-plan/by-date/{plan_date}", response_model=ProductionPlan)
async def upsert_production_plan_by_date(
	plan_date: date,
	payload: ProductionPlanCreate,
	user: dict = Depends(get_current_user)
):
	"""Create or update production plan for a specific date"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canCreate") and not access.get("canUpdate"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	# Validate all recipes exist
	for item in payload.items:
		if not await validate_recipe_exists(item.recipeId, user["restaurantId"]):
			raise HTTPException(
				status_code=status.HTTP_400_BAD_REQUEST,
				detail=f"Recipe {item.recipeId} not found"
			)

	# Upsert production plan
	items_data = [item.model_dump() for item in payload.items]
	plan_id = await repo.upsert_production_plan(
		restaurant_id=user["restaurantId"],
		plan_date=plan_date,
		items=items_data,
		status=payload.status,
		notes=payload.notes,
		based_on_forecast=payload.basedOnForecast
	)

	# Return plan
	plan = await repo.get_production_plan(plan_id, user["restaurantId"])
	return ProductionPlan(**plan)


@router.patch("/production-plan/{plan_id}", response_model=ProductionPlan)
async def update_production_plan(
	plan_id: str,
	payload: ProductionPlanUpdate,
	user: dict = Depends(get_current_user)
):
	"""Update a production plan"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canUpdate"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	# Check if plan exists
	existing = await repo.get_production_plan(plan_id, user["restaurantId"])
	if not existing:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production plan not found")

	# Build update data
	update_data = {}
	if payload.items is not None:
		# Validate all recipes exist
		for item in payload.items:
			if not await validate_recipe_exists(item.recipeId, user["restaurantId"]):
				raise HTTPException(
					status_code=status.HTTP_400_BAD_REQUEST,
					detail=f"Recipe {item.recipeId} not found"
				)
		update_data["items"] = [item.model_dump() for item in payload.items]
	if payload.status is not None:
		update_data["status"] = payload.status
	if payload.notes is not None:
		update_data["notes"] = payload.notes

	# Update
	await repo.update_production_plan(plan_id, user["restaurantId"], update_data)

	# Return updated plan
	plan = await repo.get_production_plan(plan_id, user["restaurantId"])
	return ProductionPlan(**plan)


@router.delete("/production-plan/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_production_plan(
	plan_id: str,
	user: dict = Depends(get_current_user)
):
	"""Delete a production plan"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canDelete"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	deleted = await repo.delete_production_plan(plan_id, user["restaurantId"])
	if not deleted:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production plan not found")

	return None


@router.post("/production-plan/generate-forecast")
async def generate_forecast(
	plan_date: date = Query(..., description="Date to generate forecast for"),
	forecast_days: int = Query(7, ge=1, le=90, description="Days of history to analyze"),
	user: dict = Depends(get_current_user)
):
	"""
	Generate production plan based on sales forecast.
	TODO: This is a placeholder - implement actual forecast logic.
	"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canCreate"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	forecast = await generate_plan_from_sales_forecast(
		restaurant_id=user["restaurantId"],
		plan_date=plan_date,
		forecast_days=forecast_days
	)

	return forecast
