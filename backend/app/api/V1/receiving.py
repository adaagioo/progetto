# backend/app/api/V1/receiving.py
from __future__ import annotations
from typing import List
from datetime import date
from fastapi import APIRouter, HTTPException, Depends, status, Query
from backend.app.deps.auth import get_current_user
from backend.app.core.rbac_policies import get_resource_access
from backend.app.repositories.files_repo import get_meta
from backend.app.schemas.files import FileRef
from backend.app.schemas.receiving import Receiving, ReceivingCreate
from backend.app.services.storage_service import get_storage
from backend.app.repositories.receiving_repo import (
	create_receiving, get_receiving, list_receiving, delete_receiving,
	attach_file as receiving_attach_file_repo,
	detach_file as receiving_detach_file_repo,
)

router = APIRouter()
RESOURCE = "receiving"


@router.post("/receiving", response_model=Receiving)
async def create_receiving_api(payload: ReceivingCreate, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canCreate", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	rid = await create_receiving(payload.date, [i.model_dump() for i in payload.items],
	                             actor_id=str(user["_id"]))
	doc = await get_receiving(rid)
	return Receiving(id=str(doc["_id"]), date=doc["date"], items=doc["items"], createdAt=doc["createdAt"].isoformat())


@router.get("/receiving/{rec_id}", response_model=Receiving)
async def get_receiving_api(rec_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView", True):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	doc = await get_receiving(rec_id)
	if not doc:
		raise HTTPException(status_code=404, detail="Not found")
	return Receiving(id=str(doc["_id"]), date=doc["date"], items=doc["items"], createdAt=doc["createdAt"].isoformat())


@router.get("/receiving", response_model=List[Receiving])
async def list_receiving_api(
		start: date | None = Query(None),
		end: date | None = Query(None),
		user: dict = Depends(get_current_user),
):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView", True):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	docs = await list_receiving(start=start, end=end, limit=200)
	return [Receiving(id=str(d["_id"]), date=d["date"], items=d["items"], createdAt=d["createdAt"].isoformat()) for d in
	        docs]


@router.delete("/receiving/{rec_id}")
async def delete_receiving_api(rec_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canDelete", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	ok = await delete_receiving(rec_id)
	if not ok:
		raise HTTPException(status_code=404, detail="Not found")
	return {"ok": True}


@router.post("/receiving/{rec_id}/files", response_model=FileRef, status_code=201)
async def receiving_attach_file(
		rec_id: str,
		file_id: str,
		user: dict = Depends(get_current_user)
):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canUpdate", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	meta = await get_meta(file_id)
	if not meta:
		raise HTTPException(status_code=404, detail="File not found")

	storage = get_storage()
	url = storage.get_public_url(meta["path"])

	file_ref = {
		"fileId": str(meta["_id"]),
		"filename": meta["filename"],
		"contentType": meta.get("contentType"),
		"size": meta.get("size", 0),
		"path": meta["path"],
		"url": url,
	}

	ok = await receiving_attach_file_repo(rec_id, file_ref)
	if not ok:
		raise HTTPException(status_code=404, detail="Receiving not found")

	return FileRef(**file_ref)


@router.delete("/receiving/{rec_id}/files/{file_id}")
async def receiving_detach_file(
		rec_id: str,
		file_id: str,
		user: dict = Depends(get_current_user)
):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canUpdate", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	ok = await receiving_detach_file_repo(rec_id, file_id)
	if not ok:
		raise HTTPException(status_code=404, detail="Receiving not found")
	return {"ok": True}
