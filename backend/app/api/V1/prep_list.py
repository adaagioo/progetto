# backend/app/api/V1/prep_list.py
from __future__ import annotations
from datetime import date, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from backend.app.deps.auth import get_current_user
from backend.app.core.rbac_policies import get_resource_access
from backend.app.schemas.prep_list import PrepListResponse, PrepTask, PrepForecastResponse, PrepForecastItem
from backend.app.services.prep_list_service import compute_prep_list
from backend.app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()
RESOURCE = "prep-list"


@router.get(
	"/prep-list",
	response_model=PrepListResponse,
	summary="Generate prep list for a specific date",
	description="""
	Generates the preparation task list for a given date based on the production plan.

	**What it does:**
	- Reads the production plan for the specified date
	- Analyzes all recipes in the plan
	- Aggregates preparation tasks (mise en place)
	- Calculates total quantities needed for each prep item

	**Example use case:**
	Morning of Jan 20: Check prep list to see you need 5kg of diced tomatoes,
	2kg of chopped basil, etc. for today's service.

	**Note:** Quantities are aggregated by preparation ID and unit.
	""",
	responses={
		200: {
			"description": "Prep list successfully generated",
			"content": {
				"application/json": {
					"example": {
						"date": "2025-01-20",
						"tasks": [
							{
								"preparationId": "507f1f77bcf86cd799439011",
								"name": "Pomodoro tritato",
								"preparationName": "Pomodoro tritato",
								"quantity": 6.0,
								"unit": "kg"
							},
							{
								"preparationId": "507f1f77bcf86cd799439012",
								"name": "Basilico tagliato",
								"preparationName": "Basilico tagliato",
								"quantity": 195.0,
								"unit": "g"
							}
						]
					}
				}
			}
		}
	}
)
async def prep_list(
		forDate: Optional[date] = Query(None, description="Date for which to compute prep list; defaults to today"),
		user: dict = Depends(get_current_user),
):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	d = forDate or date.today()
	logger.info(f"Computing prep list for date: {d}")
	doc = await compute_prep_list(d)
	logger.debug(f"Prep list result: {doc}")
	return PrepListResponse(**doc)


@router.get("/prep-list/forecast", response_model=PrepForecastResponse)
async def prep_list_forecast(
		start: Optional[date] = Query(None),
		days: int = Query(7, ge=1, le=31),
		user: dict = Depends(get_current_user),
):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	s = start or date.today()
	logger.info(f"Computing forecast from {s} for {days} days")
	items: List[PrepForecastItem] = []
	for i in range(days):
		current_date = s + timedelta(days=i)
		# Actually compute the prep list to get real task counts
		result = await compute_prep_list(current_date)
		tasks_count = len(result.get("tasks", []))
		logger.debug(f"Date {current_date}: {tasks_count} tasks")
		items.append(PrepForecastItem(date=current_date, tasksCount=tasks_count))
	return PrepForecastResponse(items=items)
