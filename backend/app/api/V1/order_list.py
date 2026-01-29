# backend/app/api/V1/order_list.py
from __future__ import annotations
from datetime import date, timedelta
from typing import Optional, List
from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
from backend.app.deps.auth import get_current_user
from backend.app.core.rbac_policies import get_resource_access
from backend.app.schemas.order_list import (
	OrderListResponse, OrderForecastResponse, OrderListCreate, OrderListSaved
)
from backend.app.repositories.order_list_repo import (
	compute_order_list, compute_order_forecast,
	save_order_list, get_order_list, list_order_lists
)
from backend.app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()
RESOURCE = "order-list"


@router.get(
	"/order-list",
	response_model=List[OrderListSaved],
	summary="Get all saved order lists",
	description="""
	Returns all saved order lists for the restaurant, sorted by date descending.

	**Use case:**
	Load previously saved order lists to view historical data or continue editing.
	"""
)
async def list_order_lists_endpoint(
	user: dict = Depends(get_current_user)
):
	"""Get all saved order lists for the restaurant"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	restaurant_id = user.get("restaurantId")
	if not restaurant_id:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User has no restaurant assigned")

	lists = await list_order_lists(restaurant_id)
	return [OrderListSaved(**ol) for ol in lists]


@router.get(
	"/order-list/generate",
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
	"""
)
async def generate_order_list(
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


@router.post(
	"/order-list",
	response_model=OrderListSaved,
	status_code=status.HTTP_201_CREATED,
	summary="Save an order list",
	description="""
	Save an order list with user modifications (actual quantities, supplier selections, notes).
	If an order list for the same date already exists, it will be updated.
	"""
)
async def save_order_list_endpoint(
	payload: OrderListCreate,
	user: dict = Depends(get_current_user),
):
	"""Save or update an order list"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canCreate") and not access.get("canUpdate"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	restaurant_id = user.get("restaurantId")
	if not restaurant_id:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User has no restaurant assigned")

	# Convert items to dict for storage
	items_data = [item.model_dump() for item in payload.items]

	# Save the order list
	await save_order_list(restaurant_id, payload.date, items_data)

	# Retrieve and return the saved list
	saved = await get_order_list(restaurant_id, payload.date)
	if not saved:
		raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save order list")

	logger.info(f"Saved order list for {payload.date} with {len(payload.items)} items")
	return OrderListSaved(**saved)


@router.get("/order-list/forecast")
async def order_list_forecast(
	start: date = Query(..., alias="date", description="Start date for forecast"),
	days: int = Query(1, ge=1, le=31, description="Number of days to forecast"),
	user: dict = Depends(get_current_user)
):
	"""
	Generate order list forecast.
	When days=1 (default), returns full order list for the date (OrderListResponse).
	When days>1, returns forecast counts (OrderForecastResponse).
	"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	restaurant_id = user.get("restaurantId")
	if not restaurant_id:
		logger.error(f"User {user.get('_id')} has no restaurantId")
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User has no restaurant assigned")

	today = date.today()
	if start < today - timedelta(days=90):
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Start date cannot be more than 90 days in the past")
	if start > today + timedelta(days=365):
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Start date cannot be more than 1 year in the future")

	# If single day, return full order list (for frontend "Generate" button)
	if days == 1:
		doc = await compute_order_list(start, restaurant_id)
		return OrderListResponse(**doc)

	# Multi-day forecast returns counts per day
	items = await compute_order_forecast(start, days, restaurant_id)
	return OrderForecastResponse(items=items)


@router.get("/order-list/export")
async def export_order_list(
	date_param: Optional[date] = Query(None, alias="date", description="Date for order list"),
	format: str = Query("pdf", description="Export format: pdf or xlsx"),
	locale: str = Query("en", description="Locale for export"),
	user: dict = Depends(get_current_user),
):
	"""Export order list to PDF or Excel format"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	restaurant_id = user.get("restaurantId")
	if not restaurant_id:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User has no restaurant assigned")

	target_date = date_param or (date.today() + timedelta(days=1))
	logger.info(f"Exporting order list for date {target_date} in format {format}")

	# Compute order list
	doc = await compute_order_list(target_date, restaurant_id)
	items = doc.get("items", [])

	if not items:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No items to export for the selected date")

	if format.lower() == "pdf":
		# Generate PDF
		from reportlab.pdfgen import canvas
		from reportlab.lib.pagesizes import A4

		buf = BytesIO()
		c = canvas.Canvas(buf, pagesize=A4)
		width, height = A4

		# Title
		c.setFont("Helvetica-Bold", 16)
		c.drawString(50, height - 50, f"Order List - {target_date}")

		# Column headers
		c.setFont("Helvetica-Bold", 9)
		y = height - 100
		c.drawString(50, y, "Ingredient")
		c.drawString(200, y, "Current")
		c.drawString(260, y, "Suggested")
		c.drawString(320, y, "Unit")
		c.drawString(370, y, "Supplier")
		c.drawString(470, y, "Drivers")

		y -= 20
		c.setFont("Helvetica", 8)

		for item in items:
			if y < 50:  # New page if needed
				c.showPage()
				c.setFont("Helvetica", 8)
				y = height - 50

			name = item.get("name", item.get("ingredientName", "Unknown"))
			current = item.get("currentStock", item.get("currentQty", 0))
			suggested = item.get("suggestedQty", item.get("quantity", 0))
			unit = item.get("unit", "")
			supplier = item.get("supplierName", "")
			drivers = ", ".join(item.get("drivers", []) or [])

			c.drawString(50, y, str(name)[:25])
			c.drawString(200, y, f"{current:.2f}" if current else "0")
			c.drawString(260, y, f"{suggested:.2f}" if suggested else "0")
			c.drawString(320, y, str(unit)[:10])
			c.drawString(370, y, str(supplier)[:15])
			c.drawString(470, y, str(drivers)[:20])
			y -= 15

		c.save()
		buf.seek(0)

		return Response(
			content=buf.getvalue(),
			media_type="application/pdf",
			headers={"Content-Disposition": f"attachment; filename=order_list_{target_date}.pdf"}
		)

	elif format.lower() in ["excel", "xlsx"]:
		# Generate Excel
		from openpyxl import Workbook

		wb = Workbook()
		ws = wb.active
		ws.title = "Order List"

		# Headers
		ws.append(["Order List - Date:", str(target_date)])
		ws.append([])
		ws.append(["Ingredient", "Current Stock", "Suggested Qty", "Unit", "Supplier", "Drivers", "Notes"])

		# Data
		for item in items:
			name = item.get("name", item.get("ingredientName", "Unknown"))
			current = item.get("currentStock", item.get("currentQty", 0))
			suggested = item.get("suggestedQty", item.get("quantity", 0))
			unit = item.get("unit", "")
			supplier = item.get("supplierName", "")
			drivers = ", ".join(item.get("drivers", []) or [])
			notes = item.get("notes", "")

			ws.append([name, current, suggested, unit, supplier, drivers, notes])

		buf = BytesIO()
		wb.save(buf)
		buf.seek(0)

		return Response(
			content=buf.getvalue(),
			media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
			headers={"Content-Disposition": f"attachment; filename=order_list_{target_date}.xlsx"}
		)

	else:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported format: {format}")
