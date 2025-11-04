# backend/app/api/V1/menu.py
from __future__ import annotations
from datetime import date
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from backend.app.deps.auth import get_current_user
from backend.app.core.rbac_policies import get_resource_access
from backend.app.schemas.menu import Menu, MenuCreate, MenuUpdate
from backend.app.repositories.menu_repo import get_by_date, create_menu, get_menu, update_menu, delete_menu, list_menus

router = APIRouter()
RESOURCE = "menu"


@router.get("/menu", response_model=Menu)
async def menu_get(forDate: date = Query(...), user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	doc = await get_by_date(forDate)
	if not doc:
		raise HTTPException(status_code=404, detail="Not found")
	return Menu(id=str(doc["_id"]), date=doc["date"], items=doc["items"])


@router.post("/menu", response_model=Menu, status_code=201)
async def menu_create(payload: MenuCreate, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canCreate"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	mid = await create_menu(payload.date, [i.model_dump() for i in payload.items])
	doc = await get_menu(mid)
	return Menu(id=str(doc["_id"]), date=doc["date"], items=doc["items"])


@router.put("/menu/{menu_id}", response_model=Menu)
async def menu_update(menu_id: str, payload: MenuUpdate, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canUpdate"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	ok = await update_menu(menu_id, [i.model_dump() for i in payload.items])
	if not ok:
		raise HTTPException(status_code=404, detail="Not found")
	doc = await get_menu(menu_id)
	return Menu(id=str(doc["_id"]), date=doc["date"], items=doc["items"])


@router.delete("/menu/{menu_id}", status_code=204)
async def menu_delete(menu_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canDelete"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	ok = await delete_menu(menu_id)
	if not ok:
		raise HTTPException(status_code=404, detail="Not found")
	return None


@router.get("/menu/range", response_model=List[Menu])
async def menu_range(start: Optional[date] = Query(None), end: Optional[date] = Query(None),
                     user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	docs = await list_menus(start=start, end=end, limit=200)
	return [Menu(id=str(d["_id"]), date=d["date"], items=d["items"]) for d in docs]
