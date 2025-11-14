# backend/app/api/V1/ocr.py
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from backend.app.deps.auth import get_current_user
from backend.app.core.rbac_policies import get_resource_access
from backend.app.repositories.ocr_repo import upsert_rules, list_rules, delete_rule
from backend.app.schemas.ocr import OCRStartRequest, OCRResult, OCRSaveMappingsRequest, OCRCreateReceivingRequest, \
	OCRMappingRecord
from backend.app.services.ocr_receiving_service import create_receiving_from_ocr
from backend.app.services.ocr_service import run_ocr

router = APIRouter()
RESOURCE = "ocr"


@router.post("/ocr/process", response_model=OCRResult)
async def ocr_process(payload: OCRStartRequest, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canCreate"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	return await run_ocr(payload.fileId, payload.language)


@router.post("/ocr/mappings")
async def ocr_save_mappings(payload: OCRSaveMappingsRequest, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canUpdate", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	user_id = str(user["_id"])

	rules = []
	for r in payload.rules:
		rules.append({
			"key": r.key,
			"inventoryId": r.inventoryId,
			"defaultUnit": r.defaultUnit
		})

	touched = await upsert_rules(user_id, payload.supplierId, rules)
	return {"ok": True, "updated": touched}


@router.post("/ocr/create-receiving")
async def ocr_create_receiving(payload: OCRCreateReceivingRequest, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, "receiving")
	if not access.get("canCreate", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	rec_id = await create_receiving_from_ocr(payload)
	return {"ok": True, "id": rec_id}


@router.get("/ocr/mappings", response_model=List[OCRMappingRecord])
async def ocr_list_mappings(
		supplierId: Optional[str] = Query(default=None),
		user: dict = Depends(get_current_user)
):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	user_id = str(user["_id"])

	docs = await list_rules(user_id, supplier_id=supplierId, limit=500)
	out: List[OCRMappingRecord] = []
	for d in docs:
		out.append(OCRMappingRecord(
			key=d["key"],
			inventoryId=str(d["inventoryId"]),
			defaultUnit=d.get("defaultUnit"),
			supplierId=(str(d["supplierId"]) if d.get("supplierId") else None),
		))
	return out


@router.delete("/ocr/mappings/{key}")
async def ocr_delete_mapping(
		key: str,
		supplierId: Optional[str] = Query(default=None),
		user: dict = Depends(get_current_user)
):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canUpdate", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	user_id = str(user["_id"])

	deleted = await delete_rule(user_id, key, supplier_id=supplierId)
	if deleted == 0:
		raise HTTPException(status_code=404, detail="Mapping not found")
	return {"ok": True, "deleted": deleted}


@router.post("/ocr/receivings", summary="Create Receiving from OCR parsed items")
async def create_receiving_from_ocr(payload: OCRCreateReceivingRequest = Body(...)):
	return {"ok": True}
