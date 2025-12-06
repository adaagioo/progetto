# backend/app/api/V1/wastage.py
from __future__ import annotations
from datetime import date, datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from backend.app.deps.auth import get_current_user
from backend.app.core.rbac_policies import get_resource_access
from backend.app.schemas.wastage import Wastage, WastageCreate
from backend.app.repositories import wastage_repo as repo
from backend.app.services.inventory_service import deduct_stock_for_wastage

router = APIRouter()
RESOURCE = "wastage"


@router.post("/wastage", response_model=Wastage, status_code=201)
async def wastage_create(payload: WastageCreate, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canCreate"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	items = [i.model_dump() for i in payload.items]
	wastage_doc = {
		"date": payload.date,
		"items": items,
		"restaurantId": user["restaurantId"],
		"createdAt": datetime.now(tz=timezone.utc)
	}
	wid = await repo.insert_one(wastage_doc)

	# Deduct stock with rollback on failure
	try:
		await deduct_stock_for_wastage(items, actor_id=str(user["_id"]))
	except Exception as e:
		# Rollback: delete the wastage record if stock deduction fails
		await repo.delete_one(user["restaurantId"], wid)
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail=f"Failed to deduct stock for wastage: {str(e)}"
		)

	doc = await repo.find_one(user["restaurantId"], wid)
	return Wastage(**doc)


@router.get("/wastage", response_model=List[Wastage])
async def wastage_list(
		start: Optional[date] = Query(None),
		end: Optional[date] = Query(None),
		limit: int = 100, skip: int = 0,
		user: dict = Depends(get_current_user),
):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	docs = await repo.find_many(user["restaurantId"], start=start, end=end, limit=limit, skip=skip)
	return [Wastage(**d) for d in docs]


@router.get("/wastage/{w_id}", response_model=Wastage)
async def wastage_get(w_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	d = await repo.find_one(user["restaurantId"], w_id)
	if not d:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
	return Wastage(**d)


@router.delete("/wastage/{w_id}", status_code=204)
async def wastage_delete(w_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canDelete"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	ok = await repo.delete_one(user["restaurantId"], w_id)
	if not ok:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
	return None
