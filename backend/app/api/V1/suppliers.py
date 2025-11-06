# backend/app/api/V1/suppliers.py
from __future__ import annotations
from typing import List
from fastapi import APIRouter, HTTPException, Depends, status
from backend.app.deps.auth import get_current_user
from backend.app.core.rbac_policies import get_resource_access
from backend.app.schemas.suppliers import Supplier, SupplierCreate, SupplierUpdate
from backend.app.repositories import suppliers_repo as repo

router = APIRouter()
RESOURCE = "suppliers"


@router.post("/suppliers", response_model=Supplier)
async def create_supplier(payload: SupplierCreate, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canCreate", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	sid = await repo.create(payload.model_dump(exclude_unset=True))
	doc = await repo.get_by_id(sid)
	return Supplier(id=str(doc["_id"]), **{k: v for k, v in doc.items() if k != "_id"})


@router.get("/suppliers", response_model=List[Supplier])
async def list_suppliers(user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canRead", True):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	docs = await repo.list_all()
	return [Supplier(id=str(d["_id"]), **{k: v for k, v in d.items() if k != "_id"}) for d in docs]


@router.get("/suppliers/{supplier_id}", response_model=Supplier)
async def get_supplier(supplier_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canRead", True):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	doc = await repo.get_by_id(supplier_id)
	if not doc:
		raise HTTPException(status_code=404, detail="Not found")
	return Supplier(id=str(doc["_id"]), **{k: v for k, v in doc.items() if k != "_id"})


@router.put("/suppliers/{supplier_id}", response_model=Supplier)
async def update_supplier(supplier_id: str, payload: SupplierUpdate, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canUpdate", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	ok = await repo.update(supplier_id, payload.model_dump(exclude_unset=True))
	if not ok:
		raise HTTPException(status_code=404, detail="Not found")
	doc = await repo.get_by_id(supplier_id)
	return Supplier(id=str(doc["_id"]), **{k: v for k, v in doc.items() if k != "_id"})


@router.delete("/suppliers/{supplier_id}")
async def delete_supplier(supplier_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canDelete", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	ok = await repo.delete(supplier_id)
	if not ok:
		raise HTTPException(status_code=404, detail="Not found")
	return {"ok": True}
