# backend/app/api/V1/files.py
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from fastapi.responses import StreamingResponse
from backend.app.deps.auth import get_current_user
from backend.app.core.rbac_policies import get_resource_access
from backend.app.schemas.files import FileUploadResponse
from backend.app.services.storage_service import store_file, open_file_stream, get_file_meta

router = APIRouter()
RESOURCE = "files"


@router.post("/files", response_model=FileUploadResponse, status_code=201)
async def upload_file(
		user: dict = Depends(get_current_user),
		f: UploadFile = File(...),
):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canCreate"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	file_id, length = await store_file(f.filename, f.content_type, f.file)
	return FileUploadResponse(id=file_id, filename=f.filename, contentType=f.content_type, length=length)


@router.get("/files/{file_id}")
async def download_file(file_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	meta = await get_file_meta(file_id)
	if not meta:
		raise HTTPException(status_code=404, detail="File not found")
	stream = await open_file_stream(file_id)
	headers = {"Content-Disposition": f'attachment; filename="{meta.get("filename", "file")}"'}
	return StreamingResponse(stream,
	                         media_type=meta.get("metadata", {}).get("contentType") or "application/octet-stream",
	                         headers=headers)
