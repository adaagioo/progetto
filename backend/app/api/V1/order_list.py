# backend/app/api/V1/order_list.py
from __future__ import annotations
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from backend.app.deps.auth import get_current_user
from backend.app.core.rbac_policies import get_resource_access
from backend.app.schemas.order_list import OrderListResponse, OrderForecastResponse
from backend.app.repositories.order_list_repo import compute_order_list, compute_order_forecast

router = APIRouter()
RESOURCE = "order-list"


@router.get("/order-list", response_model=OrderListResponse)
async def order_list(
	forDate: Optional[date] = Query(None, description="Date for order list; defaults to tomorrow"),
	user: dict = Depends(get_current_user)
):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	from datetime import timedelta
	target_date = forDate or (date.today() + timedelta(days=1))

	doc = await compute_order_list(target_date)
	return OrderListResponse(**doc)


@router.get("/order-list/forecast", response_model=OrderForecastResponse)
async def order_list_forecast(start: date = Query(...), days: int = Query(7, ge=1, le=31),
                              user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	items = await compute_order_forecast(start, days)
	return OrderForecastResponse(items=items)
