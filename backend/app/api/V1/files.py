# backend/app/api/V1/files.py
from __future__ import annotations
from typing import List
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, status, Response
from backend.app.deps.auth import get_current_user
from backend.app.core.rbac_policies import get_resource_access
from backend.app.schemas.files import FileMeta
from backend.app.repositories.files_repo import insert_meta, get_meta, delete_meta, list_files
from backend.app.services.storage_service import get_storage

router = APIRouter()
RESOURCE = "files"


@router.post("/files", response_model=FileMeta)
async def upload_file(f: UploadFile = File(...), user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canCreate", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	data = await f.read()
	storage = get_storage()
	path, size = storage.save_file(f.filename, f.content_type, data)
	meta_id = await insert_meta({
		"filename": f.filename,
		"contentType": f.content_type,
		"size": size,
		"path": path,
		"ownerId": str(user["_id"]) if user else None,
		"restaurantId": user["restaurantId"],  # Multi-tenancy: tie file to restaurant
	})
	doc = await get_meta(meta_id)
	return FileMeta(
		id=str(doc["_id"]),
		filename=doc["filename"],
		contentType=doc.get("contentType"),
		size=doc["size"],
		path=doc["path"],
		ownerId=str(doc["ownerId"]) if doc.get("ownerId") else None,
		createdAt=doc["createdAt"].isoformat(),
	)


@router.get("/files", response_model=List[FileMeta])
async def list_files_api(user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	# Multi-tenancy: only list files from user's restaurant
	docs = await list_files(restaurant_id=user["restaurantId"])
	out = []
	for d in docs:
		out.append(FileMeta(
			id=str(d["_id"]),
			filename=d["filename"],
			contentType=d.get("contentType"),
			size=d["size"],
			path=d["path"],
			ownerId=str(d["ownerId"]) if d.get("ownerId") else None,
			createdAt=d["createdAt"].isoformat(),
		))
	return out


@router.get("/files/{file_id}")
async def download_file(file_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	# Multi-tenancy: verify file belongs to user's restaurant
	doc = await get_meta(file_id, restaurant_id=user["restaurantId"])
	if not doc:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found or access denied")
	storage = get_storage()
	data = storage.open_file(doc["path"])
	content_type = doc.get("contentType") or "application/octet-stream"
	return Response(content=data, media_type=content_type,
	                headers={"Content-Disposition": f'attachment; filename="{doc["filename"]}"'})


@router.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file_api(file_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canDelete", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	# Multi-tenancy: verify file belongs to user's restaurant before deletion
	doc = await get_meta(file_id, restaurant_id=user["restaurantId"])
	if not doc:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found or access denied")
	storage = get_storage()
	storage.delete_file(doc["path"])
	# Multi-tenancy: delete with restaurant check
	deleted = await delete_meta(file_id, restaurant_id=user["restaurantId"])
	if not deleted:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found or access denied")
	return None
