# backend/app/api/V1/pl.py
from __future__ import annotations
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from backend.app.deps.auth import get_current_user
from backend.app.core.rbac_policies import get_resource_access
from backend.app.schemas.pl import PLResponse, PLSnapshot, PLSnapshotCreate, PL, PLCreate
from backend.app.services.pl_service import compute_pl
from backend.app.repositories import pl_repo as repo

router = APIRouter()
RESOURCE = "pl"


@router.get("/pl", response_model=PLResponse)
async def pl_get(start: date = Query(...), end: date = Query(...), user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	revenue, cogs, wastage_cost = await compute_pl(start, end)
	gross = revenue - cogs - wastage_cost
	return PLResponse(start=start, end=end, revenue=revenue, costOfGoods=cogs, wastageCost=wastage_cost,
	                  grossMargin=gross)


@router.post("/pl/snapshot", response_model=PLSnapshot, status_code=201)
async def create_pl_snapshot(payload: PLSnapshotCreate, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canCreate"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	snapshot_id = await repo.create_pl_snapshot(
		user["restaurantId"],
		payload.period.model_dump(),
		payload.currency,
		payload.displayLocale,
		payload.sales_turnover,
		payload.sales_food_beverage,
		payload.sales_delivery,
		payload.cogs_food_beverage,
		payload.cogs_raw_waste,
		payload.opex_non_food,
		payload.opex_platforms,
		payload.labour_employees,
		payload.labour_staff_meal,
		payload.marketing_online_ads,
		payload.marketing_free_items,
		payload.rent_base_effective,
		payload.rent_garden,
		payload.other_total,
		payload.notes
	)

	snapshot = await repo.get_pl_snapshot(snapshot_id, user["restaurantId"])
	return PLSnapshot(**snapshot)


@router.get("/pl/snapshot", response_model=List[PLSnapshot])
async def list_pl_snapshots(
		start_date: Optional[str] = None,
		end_date: Optional[str] = None,
		user: dict = Depends(get_current_user)
):
	"""Get P&L snapshots, optionally filtered by date range"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	snapshots = await repo.list_pl_snapshots(user["restaurantId"], start_date, end_date)
	return [PLSnapshot(**s) for s in snapshots]


@router.post("/pl/record", response_model=PL, status_code=201)
async def create_pl_record(payload: PLCreate, user: dict = Depends(get_current_user)):
	"""Create a stored P&L record"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canCreate"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	pl_id = await repo.create_pl(
		user["restaurantId"],
		payload.month,
		payload.revenue,
		payload.cogs,
		payload.grossMargin,
		payload.notes
	)

	pl_record = await repo.get_pl(pl_id, user["restaurantId"])
	return PL(**pl_record)


@router.get("/pl/records", response_model=List[PL])
async def list_pl_records(user: dict = Depends(get_current_user)):
	"""Get all stored P&L records"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	records = await repo.list_pl(user["restaurantId"])
	return [PL(**p) for p in records]


@router.delete("/pl/record/{pl_id}")
async def delete_pl_record(pl_id: str, user: dict = Depends(get_current_user)):
	"""Delete a stored P&L record"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canDelete"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	deleted = await repo.delete_pl(pl_id, user["restaurantId"])
	if not deleted:
		raise HTTPException(status_code=404, detail="P&L record not found")

	return {"message": "P&L record deleted"}
