# backend/app/api/V1/exports.py
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from io import BytesIO
from app.deps.auth import get_current_user
from app.core.rbac_utils import get_resource_access
from app.repositories.recipes_repo import find_many as find_recipes
from app.repositories.ingredients_repo import find_many as find_ingredients
from openpyxl import Workbook
from reportlab.pdfgen import canvas

router = APIRouter()
PREPLIST_RESOURCE = "preplist"
ORDERLIST_RESOURCE = "orderlist"


def _xlsx_response(wb: Workbook, filename: str) -> StreamingResponse:
	buf = BytesIO()
	wb.save(buf)
	buf.seek(0)
	return StreamingResponse(
		buf,
		media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
		headers={"Content-Disposition": f"attachment; filename={filename}"}
	)


def _pdf_response(draw_fn, filename: str) -> StreamingResponse:
	buf = BytesIO()
	c = canvas.Canvas(buf)
	draw_fn(c)
	c.showPage()
	c.save()
	buf.seek(0)
	return StreamingResponse(
		buf,
		media_type="application/pdf",
		headers={"Content-Disposition": f"attachment; filename={filename}"}
	)


@router.get("/exports/preplist.xlsx")
async def export_preplist_xlsx(user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, PREPLIST_RESOURCE)
	if not access["canView"]:
		raise HTTPException(status_code=403, detail="Forbidden")
	recipes = await find_recipes(user["restaurantId"])
	wb = Workbook()
	ws = wb.active
	ws.title = "PrepList"
	ws.append(["Recipe", "Portions", "#Items"])
	for r in recipes:
		ws.append([r.get("name"), r.get("portions"), len(r.get("items") or [])])
	return _xlsx_response(wb, "preplist.xlsx")


@router.get("/exports/preplist.pdf")
async def export_preplist_pdf(user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, PREPLIST_RESOURCE)
	if not access["canView"]:
		raise HTTPException(status_code=403, detail="Forbidden")

	def draw(c):
		c.setFont("Helvetica", 12)
		c.drawString(50, 800, "PrepList (summary)")

	return _pdf_response(draw, "preplist.pdf")


@router.get("/exports/orderlist.xlsx")
async def export_orderlist_xlsx(user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, ORDERLIST_RESOURCE)
	if not access["canView"]:
		raise HTTPException(status_code=403, detail="Forbidden")
	ingredients = await find_ingredients(user["restaurantId"])
	wb = Workbook()
	ws = wb.active
	ws.title = "OrderList"
	ws.append(["Ingredient", "Unit", "SKU"])
	for ing in ingredients:
		ws.append([ing.get("name"), ing.get("unit"), ing.get("sku")])
	return _xlsx_response(wb, "orderlist.xlsx")


@router.get("/exports/orderlist.pdf")
async def export_orderlist_pdf(user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, ORDERLIST_RESOURCE)
	if not access["canView"]:
		raise HTTPException(status_code=403, detail="Forbidden")

	def draw(c):
		c.setFont("Helvetica", 12)
		c.drawString(50, 800, "OrderList (summary)")

	return _pdf_response(draw, "orderlist.pdf")
