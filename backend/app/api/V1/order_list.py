# backend/app/api/V1/order_list.py
from __future__ import annotations
from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from backend.app.deps.auth import get_current_user
from backend.app.core.rbac_policies import get_resource_access
from backend.app.schemas.order_list import OrderListResponse, OrderForecastResponse
from backend.app.repositories.order_list_repo import compute_order_list, compute_order_forecast
from backend.app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()
RESOURCE = "order-list"


@router.get(
	"/order-list",
	response_model=OrderListResponse,
	summary="Generate order list for a specific date",
	description="""
	Generates a smart order list based on:
	- **Current inventory levels** aggregated by ingredient
	- **Planned consumption** from production plans (next 7 days)
	- **Reorder levels** configured for each ingredient

	The system calculates projected stock levels and suggests orders for items
	that will fall below their reorder threshold.

	**Algorithm:**
	1. Aggregate current inventory by ingredient
	2. Calculate consumption from upcoming production plans
	3. Compute: `projected = current - planned_consumption`
	4. If `projected < reorder_level`, suggest ordering `target_level - projected`

	**Use case:** Daily review of what needs to be ordered from suppliers
	""",
	responses={
		200: {
			"description": "Order list successfully generated",
			"content": {
				"application/json": {
					"example": {
						"date": "2025-01-21",
						"items": [
							{
								"inventoryId": "507f1f77bcf86cd799439011",
								"name": "Fresh Basil",
								"quantity": 2.5,
								"unit": "kg",
								"supplierId": "507f191e810c19729de860ea",
								"currentStock": 1.2,
								"plannedConsumption": 3.5,
								"projectedStock": -2.3,
								"reorderLevel": 0.5,
								"targetLevel": 5.0
							}
						]
					}
				}
			}
		}
	}
)
async def order_list(
	forDate: Optional[date] = Query(None, description="Date for order list; defaults to tomorrow"),
	user: dict = Depends(get_current_user)
):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	# Validate user has restaurantId
	restaurant_id = user.get("restaurantId")
	if not restaurant_id:
		logger.error(f"User {user.get('_id')} has no restaurantId")
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User has no restaurant assigned")

	target_date = forDate or (date.today() + timedelta(days=1))

	# Validate date is not too far in the past or future
	today = date.today()
	if target_date < today - timedelta(days=90):
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Date cannot be more than 90 days in the past")
	if target_date > today + timedelta(days=365):
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Date cannot be more than 1 year in the future")

	doc = await compute_order_list(target_date, restaurant_id)
	return OrderListResponse(**doc)


@router.get(
	"/order-list/forecast",
	response_model=OrderForecastResponse,
	summary="Get order forecast for multiple days",
	description="""
	Generates a multi-day forecast showing the number of items that will need
	ordering for each day in the specified range.

	Useful for:
	- **Planning ahead** - See upcoming order volumes
	- **Supplier coordination** - Schedule deliveries in advance
	- **Budget forecasting** - Estimate weekly/monthly order costs

	**Note:** This endpoint returns counts only. For detailed item lists,
	call `/order-list` for each specific date.
	""",
	responses={
		200: {
			"description": "Forecast successfully generated",
			"content": {
				"application/json": {
					"example": {
						"items": [
							{"date": "2025-01-20", "itemsCount": 5},
							{"date": "2025-01-21", "itemsCount": 3},
							{"date": "2025-01-22", "itemsCount": 7}
						]
					}
				}
			}
		}
	}
)
async def order_list_forecast(
	start: date = Query(..., alias="date", description="Start date for forecast"),
	days: int = Query(7, ge=1, le=31, description="Number of days to forecast"),
	user: dict = Depends(get_current_user)
):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	# Validate user has restaurantId
	restaurant_id = user.get("restaurantId")
	if not restaurant_id:
		logger.error(f"User {user.get('_id')} has no restaurantId")
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User has no restaurant assigned")

	# Validate start date is reasonable
	today = date.today()
	if start < today - timedelta(days=90):
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Start date cannot be more than 90 days in the past")
	if start > today + timedelta(days=365):
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Start date cannot be more than 1 year in the future")

	items = await compute_order_forecast(start, days, restaurant_id)
	return OrderForecastResponse(items=items)
