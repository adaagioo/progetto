# backend/app/api/V1/wastage.py
from __future__ import annotations
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from backend.app.deps.auth import get_current_user
from backend.app.core.rbac_policies import get_resource_access
from backend.app.schemas.wastage import Wastage, WastageCreate
from backend.app.repositories.wastage_repo import create_wastage, get_wastage, list_wastage, delete_wastage
from backend.app.services.inventory_service import deduct_stock_for_wastage

router = APIRouter()
RESOURCE = "wastage"


@router.post("/wastage", response_model=Wastage, status_code=201)
async def wastage_create(payload: WastageCreate, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canCreate"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	items = [i.model_dump() for i in payload.items]
	wid = await create_wastage(payload.date, items)
	await deduct_stock_for_wastage(items, actor_id=str(user["_id"]))
	doc = await get_wastage(wid)
	return Wastage(id=str(doc["_id"]), date=doc["date"], items=doc["items"], createdAt=doc["createdAt"])


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
	docs = await list_wastage(start=start, end=end, limit=limit, skip=skip)
	return [Wastage(id=str(d["_id"]), date=d["date"], items=d["items"], createdAt=d["createdAt"]) for d in docs]


@router.get("/wastage/{w_id}", response_model=Wastage)
async def wastage_get(w_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	d = await get_wastage(w_id)
	if not d:
		raise HTTPException(status_code=404, detail="Not found")
	return Wastage(id=str(d["_id"]), date=d["date"], items=d["items"], createdAt=d["createdAt"])


@router.delete("/wastage/{w_id}", status_code=204)
async def wastage_delete(w_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canDelete"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	ok = await delete_wastage(w_id)
	if not ok:
		raise HTTPException(status_code=404, detail="Not found")
	return None
