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
		"ownerId": (user.get("id") if isinstance(user, dict) else None),
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
	if not access.get("canRead", True):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	docs = await list_files()
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
	if not access.get("canRead", True):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	doc = await get_meta(file_id)
	if not doc:
		raise HTTPException(status_code=404, detail="Not found")
	storage = get_storage()
	data = storage.open_file(doc["path"])
	content_type = doc.get("contentType") or "application/octet-stream"
	return Response(content=data, media_type=content_type,
	                headers={"Content-Disposition": f'attachment; filename="{doc["filename"]}"'})


@router.delete("/files/{file_id}")
async def delete_file_api(file_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canDelete", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	doc = await get_meta(file_id)
	if not doc:
		raise HTTPException(status_code=404, detail="Not found")
	storage = get_storage()
	storage.delete_file(doc["path"])
	await delete_meta(file_id)
	return {"ok": True}
