# backend/app/api/V1/suppliers.py
from __future__ import annotations
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from backend.app.deps.auth import get_current_user
from backend.app.core.rbac_policies import get_resource_access
from backend.app.schemas.suppliers import SupplierCreate, SupplierUpdate, Supplier
from backend.app.repositories.suppliers_repo import (
	create_supplier, get_supplier, list_suppliers, update_supplier, delete_supplier
)

router = APIRouter()
RESOURCE = "suppliers"


@router.post("/suppliers", response_model=Supplier, status_code=201)
async def suppliers_create(payload: SupplierCreate, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canCreate"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	sid = await create_supplier(payload.model_dump(exclude_unset=True))
	doc = await get_supplier(sid)
	return Supplier(id=sid, name=doc["name"], email=doc.get("email"), phone=doc.get("phone"))


@router.get("/suppliers", response_model=List[Supplier])
async def suppliers_list(limit: int = 50, skip: int = 0, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	docs = await list_suppliers(limit=limit, skip=skip)
	return [Supplier(id=str(d["_id"]), name=d["name"], email=d.get("email"), phone=d.get("phone")) for d in docs]


@router.get("/suppliers/{supplier_id}", response_model=Supplier)
async def suppliers_get(supplier_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	d = await get_supplier(supplier_id)
	if not d:
		raise HTTPException(status_code=404, detail="Not found")
	return Supplier(id=str(d["_id"]), name=d["name"], email=d.get("email"), phone=d.get("phone"))


@router.put("/suppliers/{supplier_id}", response_model=Supplier)
async def suppliers_update(supplier_id: str, payload: SupplierUpdate, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canUpdate"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	ok = await update_supplier(supplier_id, payload.model_dump(exclude_unset=True))
	if not ok:
		raise HTTPException(status_code=404, detail="Not found")
	d = await get_supplier(supplier_id)
	return Supplier(id=str(d["_id"]), name=d["name"], email=d.get("email"), phone=d.get("phone"))


@router.delete("/suppliers/{supplier_id}", status_code=204)
async def suppliers_delete(supplier_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canDelete"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	ok = await delete_supplier(supplier_id)
	if not ok:
		raise HTTPException(status_code=404, detail="Not found")
	return None
