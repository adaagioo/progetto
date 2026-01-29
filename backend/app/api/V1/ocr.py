# backend/app/api/V1/ocr.py
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, UploadFile, File, Form
from backend.app.deps.auth import get_current_user
from backend.app.core.rbac_policies import get_resource_access
from backend.app.repositories.ocr_repo import upsert_rules, list_rules, delete_rule
from backend.app.repositories.files_repo import insert_meta
from backend.app.schemas.ocr import (
	OCRStartRequest, OCRResult, OCRSaveMappingsRequest, OCRCreateReceivingRequest,
	OCRMappingRecord, OCRProcessResponse, OCRProcessResponseOcr, OCRProcessResponseParsed,
	OCRCreateReceivingFrontend
)
from backend.app.services.ocr_receiving_service import create_receiving_from_ocr
from backend.app.services.ocr_service import run_ocr
from backend.app.services.storage_service import get_storage

router = APIRouter()
RESOURCE = "ocr"


@router.post("/ocr/process", response_model=OCRProcessResponse)
async def ocr_process(
	file: UploadFile = File(...),
	lang: str = Form("eng"),
	user: dict = Depends(get_current_user)
):
	"""Upload and process a file with OCR - returns format expected by frontend"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canCreate"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	# Upload file to storage
	data = await file.read()
	storage = get_storage()
	path, size = storage.save_file(file.filename, file.content_type, data)

	# Create file metadata
	meta_id = await insert_meta({
		"filename": file.filename,
		"contentType": file.content_type,
		"size": size,
		"path": path,
		"ownerId": str(user.get("_id")) if user.get("_id") else None,
	})

	# Run OCR on the uploaded file
	ocr_result = await run_ocr(meta_id, lang)

	# Transform to frontend-expected format
	parsed_data = ocr_result.meta.get("parsed", {})

	# Calculate average confidence from lines
	avg_confidence = 0.0
	if ocr_result.lines:
		avg_confidence = sum(line.confidence for line in ocr_result.lines) / len(ocr_result.lines)

	# Transform items to line_items format expected by frontend
	line_items = []
	for item in parsed_data.get("items", []):
		line_items.append({
			"description": item.get("name", ""),
			"qty": item.get("qty", 0),
			"unit": item.get("unit", ""),
			"price": item.get("unitCost", 0),
			"matches": item.get("matches", []),
		})

	return OCRProcessResponse(
		ok=ocr_result.ok,
		ocr=OCRProcessResponseOcr(
			lines=ocr_result.lines,
			confidence=avg_confidence
		),
		parsed=OCRProcessResponseParsed(
			date=parsed_data.get("date"),
			supplier_name=parsed_data.get("supplier"),
			invoice_number=None,  # Not currently parsed
			document_type=None,  # Not currently parsed
			currency=parsed_data.get("currency"),
			line_items=line_items
		)
	)


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
async def ocr_create_receiving(
	payload: OCRCreateReceivingFrontend,
	user: dict = Depends(get_current_user)
):
	"""Create a receiving record from OCR-parsed document data (frontend format)"""
	access = await get_resource_access(user, "receiving")
	if not access.get("canCreate", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	from backend.app.repositories.receiving_repo import insert_one
	from datetime import datetime, timezone, date

	restaurant_id = user.get("restaurantId")
	if not restaurant_id:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User has no restaurant assigned")

	# Parse date
	arrived_at = date.today()
	if payload.date:
		try:
			arrived_at = datetime.fromisoformat(payload.date).date()
		except (ValueError, TypeError):
			pass

	# Convert line items to receiving format
	lines = []
	for item in payload.lineItems:
		lines.append({
			"ingredientId": item.ingredientId,
			"qty": item.qty,
			"unit": item.unit,
			"unitPrice": int(item.unitPrice * 100) if item.unitPrice else 0,  # Convert to minor units
			"description": item.description,
			"packFormat": item.packFormat,
		})

	# Create receiving document
	doc = {
		"restaurantId": restaurant_id,
		"arrivedAt": arrived_at.isoformat(),
		"supplierId": payload.supplierId,
		"category": payload.category,
		"lines": lines,
		"notes": f"Imported from OCR. Invoice: {payload.invoiceNumber or 'N/A'}",
		"createdAt": datetime.now(tz=timezone.utc).isoformat(),
	}

	rec_id = await insert_one(doc)
	return {"ok": True, "id": rec_id}


@router.get("/ocr/mappings/{supplier_id}", response_model=List[OCRMappingRecord])
async def ocr_list_mappings_by_supplier(
		supplier_id: str,
		user: dict = Depends(get_current_user)
):
	"""Get OCR mappings for a specific supplier (path parameter)"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	user_id = str(user["_id"])

	docs = await list_rules(user_id, supplier_id=supplier_id, limit=500)
	out: List[OCRMappingRecord] = []
	for d in docs:
		out.append(OCRMappingRecord(
			key=d["key"],
			inventoryId=str(d["inventoryId"]),
			defaultUnit=d.get("defaultUnit"),
			supplierId=(str(d["supplierId"]) if d.get("supplierId") else None),
		))
	return out


@router.get("/ocr/mappings", response_model=List[OCRMappingRecord])
async def ocr_list_mappings(
		supplierId: Optional[str] = Query(default=None),
		user: dict = Depends(get_current_user)
):
	"""Get OCR mappings (query parameter, for backwards compatibility)"""
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


@router.delete("/ocr/mappings/{key}", status_code=status.HTTP_204_NO_CONTENT)
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
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")
	return None


@router.post("/ocr/receivings", summary="Create Receiving from OCR parsed items")
async def create_receiving_from_ocr(payload: OCRCreateReceivingRequest = Body(...)):
	return {"ok": True}
