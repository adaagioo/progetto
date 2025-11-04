# backend/app/api/V1/receiving.py
from __future__ import annotations
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from backend.app.deps.auth import get_current_user
from backend.app.core.rbac_policies import get_resource_access
from backend.app.schemas.receiving import ReceivingCreate, Receiving, ReceivingAttachFileRequest
from backend.app.repositories.receiving_repo import create_receiving, get_receiving, list_receivings, attach_file, \
	list_files

router = APIRouter()
RESOURCE = "receiving"


@router.post("/receiving", response_model=Receiving, status_code=201)
async def receiving_create(payload: ReceivingCreate, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canCreate"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	rec_id = await create_receiving(payload.supplierId, payload.date, [i.model_dump() for i in payload.items])
	doc = await get_receiving(rec_id)
	return Receiving(
		id=str(doc["_id"]),
		supplierId=str(doc["supplierId"]),
		date=doc["date"],
		items=doc["items"],
		createdAt=doc["createdAt"],
	)


@router.get("/receiving", response_model=List[Receiving])
async def receiving_list(limit: int = 50, skip: int = 0, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	docs = await list_receivings(limit=limit, skip=skip)
	return [Receiving(
		id=str(d["_id"]),
		supplierId=str(d["supplierId"]),
		date=d["date"],
		items=d["items"],
		createdAt=d["createdAt"],
	) for d in docs]


@router.get("/receiving/{rec_id}", response_model=Receiving)
async def receiving_get(rec_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	d = await get_receiving(rec_id)
	if not d:
		raise HTTPException(status_code=404, detail="Not found")
	return Receiving(
		id=str(d["_id"]),
		supplierId=str(d["supplierId"]),
		date=d["date"],
		items=d["items"],
		createdAt=d["createdAt"],
	)


@router.post("/receiving/{rec_id}/files", status_code=204)
async def receiving_attach_file(rec_id: str, payload: ReceivingAttachFileRequest,
                                user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canUpdate"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	await attach_file(rec_id, payload.fileId)
	return None


@router.get("/receiving/{rec_id}/files", response_model=List[str])
async def receiving_files(rec_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	return await list_files(rec_id)
