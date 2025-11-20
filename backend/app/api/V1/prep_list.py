# backend/app/api/V1/prep_list.py
from __future__ import annotations
from datetime import date, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from backend.app.deps.auth import get_current_user
from backend.app.core.rbac_policies import get_resource_access
from backend.app.schemas.prep_list import PrepListResponse, PrepTask, PrepForecastResponse, PrepForecastItem
from backend.app.services.prep_list_service import compute_prep_list

router = APIRouter()
RESOURCE = "prep-list"


@router.get("/prep-list", response_model=PrepListResponse)
async def prep_list(
		forDate: Optional[date] = Query(None, description="Date for which to compute prep list; defaults to today"),
		user: dict = Depends(get_current_user),
):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	d = forDate or date.today()
	print(f"[PREP_LIST API] Computing prep list for date: {d}")
	doc = await compute_prep_list(d)
	print(f"[PREP_LIST API] Result: {doc}")
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
	print(f"[PREP_LIST FORECAST] Computing forecast from {s} for {days} days")
	items: List[PrepForecastItem] = []
	for i in range(days):
		current_date = s + timedelta(days=i)
		# Actually compute the prep list to get real task counts
		result = await compute_prep_list(current_date)
		tasks_count = len(result.get("tasks", []))
		print(f"[PREP_LIST FORECAST] Date {current_date}: {tasks_count} tasks")
		items.append(PrepForecastItem(date=current_date, tasksCount=tasks_count))
	return PrepForecastResponse(items=items)
