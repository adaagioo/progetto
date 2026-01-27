# backend/app/api/V1/prep_list.py
from __future__ import annotations
from datetime import date, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
from backend.app.deps.auth import get_current_user
from backend.app.core.rbac_policies import get_resource_access
from backend.app.schemas.prep_list import PrepListResponse, PrepTask, PrepForecastResponse, PrepForecastItem
from backend.app.services.prep_list_service import compute_prep_list
from backend.app.utils.logger import get_logger
from io import BytesIO

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


@router.get("/prep-list/forecast")
async def prep_list_forecast(
		start: Optional[date] = Query(None, alias="date"),
		days: int = Query(1, ge=1, le=31),
		user: dict = Depends(get_current_user),
):
	"""
	Generate prep list forecast.
	When days=1 (default), returns full prep list for the date (PrepListResponse).
	When days>1, returns forecast counts (PrepForecastResponse).
	"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	s = start or date.today()
	logger.info(f"Computing forecast from {s} for {days} days")

	# If single day, return full prep list (for frontend "Generate" button)
	if days == 1:
		doc = await compute_prep_list(s)
		return PrepListResponse(**doc)

	# Multi-day forecast returns counts per day
	items: List[PrepForecastItem] = []
	for i in range(days):
		current_date = s + timedelta(days=i)
		result = await compute_prep_list(current_date)
		tasks_count = len(result.get("tasks", []))
		logger.debug(f"Date {current_date}: {tasks_count} tasks")
		items.append(PrepForecastItem(date=current_date, tasksCount=tasks_count))
	return PrepForecastResponse(items=items)


@router.get("/prep-list/export")
async def export_prep_list(
	date_param: Optional[date] = Query(None, alias="date", description="Date for prep list"),
	format: str = Query("pdf", description="Export format: pdf or excel"),
	locale: str = Query("en", description="Locale for export"),
	user: dict = Depends(get_current_user),
):
	"""Export prep list to PDF or Excel format"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	d = date_param or date.today()
	logger.info(f"Exporting prep list for date {d} in format {format}")

	# Compute prep list
	doc = await compute_prep_list(d)
	tasks = doc.get("tasks", [])

	if format.lower() == "pdf":
		# Generate PDF
		from reportlab.pdfgen import canvas
		from reportlab.lib.pagesizes import A4

		buf = BytesIO()
		c = canvas.Canvas(buf, pagesize=A4)
		width, height = A4

		# Title
		c.setFont("Helvetica-Bold", 16)
		c.drawString(50, height - 50, f"Prep List - {d}")

		# Tasks
		c.setFont("Helvetica", 10)
		y = height - 100
		c.drawString(50, y, "Task")
		c.drawString(300, y, "Quantity")
		c.drawString(400, y, "Unit")

		y -= 20
		c.setFont("Helvetica", 9)

		for task in tasks:
			if y < 50:  # New page if needed
				c.showPage()
				c.setFont("Helvetica", 9)
				y = height - 50

			name = task.get("name", task.get("preparationName", "Unknown"))
			qty = task.get("quantity", 0)
			unit = task.get("unit", "")

			c.drawString(50, y, str(name)[:40])
			c.drawString(300, y, str(qty))
			c.drawString(400, y, str(unit))
			y -= 15

		c.save()
		buf.seek(0)

		return Response(
			content=buf.getvalue(),
			media_type="application/pdf",
			headers={"Content-Disposition": f"attachment; filename=prep_list_{d}.pdf"}
		)

	elif format.lower() in ["excel", "xlsx"]:
		# Generate Excel
		from openpyxl import Workbook

		wb = Workbook()
		ws = wb.active
		ws.title = "Prep List"

		# Headers
		ws.append(["Date", str(d)])
		ws.append([])
		ws.append(["Task", "Quantity", "Unit"])

		# Data
		for task in tasks:
			name = task.get("name", task.get("preparationName", "Unknown"))
			qty = task.get("quantity", 0)
			unit = task.get("unit", "")
			ws.append([name, qty, unit])

		buf = BytesIO()
		wb.save(buf)
		buf.seek(0)

		return Response(
			content=buf.getvalue(),
			media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
			headers={"Content-Disposition": f"attachment; filename=prep_list_{d}.xlsx"}
		)

	else:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported format: {format}")
