# backend/app/api/V1/dashboard.py
from __future__ import annotations
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from backend.app.deps.auth import get_current_user
from backend.app.core.rbac_policies import get_resource_access
from backend.app.schemas.dashboard import KPIResponse
from backend.app.services.dashboard_service import get_kpis

router = APIRouter()
RESOURCE = "dashboard"


@router.get(
	"/dashboard/kpis",
	response_model=KPIResponse,
	summary="Get dashboard KPIs with real food cost %",
	description="""
	Returns key performance indicators including:
	- Entity counts (recipes, ingredients, inventory, suppliers, sales)
	- **Total Sales** - Revenue for the specified period
	- **Value Usage** - Cost of goods used (purchases + wastage)
	- **Food Cost %** - Real food cost percentage (value usage / total sales * 100)

	**Date Range**: Defaults to last 30 days if not specified.
	"""
)
async def dashboard_kpis(
	start_date: Optional[date] = Query(None, description="Start date for calculations (defaults to 30 days ago)"),
	end_date: Optional[date] = Query(None, description="End date for calculations (defaults to today)"),
	user: dict = Depends(get_current_user)
):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	data = await get_kpis(start_date, end_date)
	return KPIResponse(**data)
