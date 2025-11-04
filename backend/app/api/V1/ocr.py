# backend/app/api/V1/ocr.py
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from backend.app.deps.auth import get_current_user
from backend.app.core.rbac_policies import get_resource_access
from backend.app.schemas.ocr import OCRStartRequest, OCRResult
from backend.app.services.ocr_service import run_ocr

router = APIRouter()
RESOURCE = "ocr"


@router.post("/ocr/process", response_model=OCRResult)
async def ocr_process(payload: OCRStartRequest, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canCreate"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	return await run_ocr(payload.fileId, payload.language)
