# backend/app/api/V1/receiving.py
from __future__ import annotations
from typing import List
from datetime import date, datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, status, Query, Request, Body, UploadFile, File
from pydantic import ValidationError, BaseModel
from backend.app.deps.auth import get_current_user
from backend.app.core.rbac_policies import get_resource_access
from backend.app.repositories.files_repo import get_meta
from backend.app.schemas.files import FileRef
from backend.app.schemas.receiving import Receiving, ReceivingPost, ReceivingUpdate
from backend.app.services.storage_service import get_storage
from backend.app.repositories import receiving_repo as repo
from backend.app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()
RESOURCE = "receiving"


@router.post("/receiving", response_model=Receiving)
async def create_receiving_api(request: Request, user: dict = Depends(get_current_user)):
	# Debug: log raw request body
	try:
		body = await request.json()
		logger.debug(f"Raw body received: {body}")
	except Exception as e:
		logger.error(f"Failed to parse request body: {e}")
		raise HTTPException(status_code=400, detail="Invalid JSON")

	# Validate payload
	try:
		payload = ReceivingPost(**body)
		logger.debug(f"Validated payload: {payload}")
	except ValidationError as e:
		logger.error(f"Validation error: {e}")
		logger.error(f"Validation errors detail: {e.errors()}")
		raise HTTPException(status_code=422, detail=e.errors())

	access = await get_resource_access(user, RESOURCE)
	if not access.get("canCreate", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	# Map ingredientId to inventoryId for each item
	from backend.app.repositories.inventory_repo import find_by_ingredient_id

	# Process items and find inventory IDs for stock updates
	items_for_db = []
	inventory_updates = []

	for item in payload.lines:
		item_dict = item.model_dump()
		ingredient_id = item_dict.get("ingredientId")

		# Save item with frontend field names for schema compatibility
		items_for_db.append(item_dict)

		# Find inventory ID for stock update
		if ingredient_id:
			try:
				inventory = await find_by_ingredient_id(
					user.get("restaurantId", "default"),
					ingredient_id
				)

				if inventory:
					inventory_id = inventory["id"]
					logger.debug(f"Mapped ingredientId {ingredient_id} to inventoryId {inventory_id}")
				else:
					# No inventory found - use ingredient ID directly
					inventory_id = ingredient_id
					logger.warning(f"No inventory found for ingredientId {ingredient_id}, using ingredient ID as inventoryId")

				# Store for inventory update with backend field names
				inventory_updates.append({
					"inventoryId": inventory_id,
					"quantity": item_dict.get("qty", 0),
					"unit": item_dict.get("unit"),
					"unitCost": item_dict.get("unitPrice"),
					"supplierId": item_dict.get("supplierId"),
					"notes": item_dict.get("notes"),
				})
			except Exception as e:
				logger.error(f"Failed to map ingredientId to inventoryId: {e}")

	# Create receiving document with frontend field names and metadata
	receiving_doc = {
		"date": payload.arrivedAt,
		"items": items_for_db,
		"restaurantId": user["restaurantId"],
		"supplierId": payload.supplierId,
		"category": payload.category,
		"notes": payload.notes,
		"createdAt": datetime.now(tz=timezone.utc)
	}
	rid = await repo.insert_one(receiving_doc)
	actor_id = str(user["_id"])

	# Apply inventory updates separately
	if inventory_updates:
		from backend.app.repositories.receiving_repo import _inc_stock, _log, _inventory, _movements
		from bson import ObjectId

		for update in inventory_updates:
			inv_id_str = update.get("inventoryId")
			qty = float(update.get("quantity", 0.0))
			unit = update.get("unit")

			if not inv_id_str or qty <= 0:
				continue

			try:
				inv_id = ObjectId(inv_id_str)
				inv_doc = await _inventory().find_one({"_id": inv_id}, projection={"unit": 1})
				inv_unit = inv_doc.get("unit") if inv_doc else None

				qty_inc = qty
				if unit and inv_unit:
					from backend.app.services.unit_conversion import convert_quantity
					qty_inc = convert_quantity(qty, unit, inv_unit)

				ok = await _inc_stock(inv_id, qty_inc)
				if ok:
					payload_log = {
						"inventoryId": inv_id,
						"qty": qty_inc,
						"unitCost": update.get("unitCost"),
						"supplierId": (ObjectId(update["supplierId"]) if update.get("supplierId") else None),
						"actorId": (ObjectId(actor_id) if actor_id else None),
						"receivingId": ObjectId(rid),
					}
					await _log("receiving", payload_log)
			except Exception as e:
				logger.error(f"Failed to update inventory: {e}")
	doc = await repo.find_one(user["restaurantId"], rid)
	return Receiving(
		id=doc["id"],
		date=doc["date"],
		items=doc["items"],
		createdAt=doc["createdAt"].isoformat(),
		restaurantId=doc["restaurantId"],
		supplierId=doc.get("supplierId"),
		category=doc.get("category"),
		notes=doc.get("notes"),
		files=doc.get("files", [])
	)


@router.get("/receiving/{rec_id}", response_model=Receiving)
async def get_receiving_api(rec_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	doc = await repo.find_one(user["restaurantId"], rec_id)
	if not doc:
		raise HTTPException(status_code=404, detail="Not found")
	return Receiving(
		id=doc["id"],
		date=doc["date"],
		items=doc["items"],
		createdAt=doc["createdAt"].isoformat(),
		restaurantId=doc["restaurantId"],
		supplierId=doc.get("supplierId"),
		category=doc.get("category"),
		notes=doc.get("notes"),
		files=doc.get("files", [])
	)


@router.put("/receiving/{rec_id}", response_model=Receiving)
@router.patch("/receiving/{rec_id}", response_model=Receiving)
async def update_receiving_api(rec_id: str, body: ReceivingUpdate, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canUpdate", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	# Build update dict with only non-None fields
	updates = {}
	if body.arrivedAt is not None:
		updates["date"] = body.arrivedAt
	if body.lines is not None:
		updates["items"] = [item.model_dump() for item in body.lines]
	if body.supplierId is not None:
		updates["supplierId"] = body.supplierId
	if body.category is not None:
		updates["category"] = body.category
	if body.notes is not None:
		updates["notes"] = body.notes

	if not updates:
		raise HTTPException(status_code=400, detail="No fields to update")

	ok = await repo.update_one(user["restaurantId"], rec_id, updates)
	if not ok:
		raise HTTPException(status_code=404, detail="Receiving not found")

	# Return updated document
	doc = await repo.find_one(user["restaurantId"], rec_id)
	return Receiving(
		id=doc["id"],
		date=doc["date"],
		items=doc["items"],
		createdAt=doc["createdAt"].isoformat(),
		restaurantId=doc["restaurantId"],
		supplierId=doc.get("supplierId"),
		category=doc.get("category"),
		notes=doc.get("notes"),
		files=doc.get("files", [])
	)


@router.get("/receiving", response_model=List[Receiving])
async def list_receiving_api(
		start: date | None = Query(None),
		end: date | None = Query(None),
		user: dict = Depends(get_current_user),
):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	docs = await repo.find_many(user["restaurantId"], start=start, end=end, limit=200)

	result = []
	for d in docs:
		try:
			receiving = Receiving(
				id=d["id"],
				date=d["date"],
				items=d.get("items", []),
				createdAt=d["createdAt"].isoformat(),
				restaurantId=d["restaurantId"],
				supplierId=d.get("supplierId"),
				category=d.get("category"),
				notes=d.get("notes"),
				files=d.get("files", [])
			)
			result.append(receiving)
			logger.debug(f"Python repr: {receiving.model_dump()}")
			logger.debug(f"JSON mode: {receiving.model_dump(mode='json')}")
		except Exception as e:
			logger.error(f"Failed to serialize receiving {d.get('id')}: {e}")
			logger.error(f"Document: {d}")

	logger.debug(f"Returning {len(result)} receivings")
	return result


@router.delete("/receiving/{rec_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_receiving_api(rec_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canDelete", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	ok = await repo.delete_one(user["restaurantId"], rec_id)
	if not ok:
		raise HTTPException(status_code=404, detail="Not found")
	return None


@router.post("/receiving/{rec_id}/files", response_model=FileRef, status_code=201)
async def receiving_attach_file(
		rec_id: str,
		file: UploadFile = File(...),
		user: dict = Depends(get_current_user)
):
	"""Upload and attach a file to a receiving"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canUpdate", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	# Upload file to storage
	data = await file.read()
	storage = get_storage()
	path, size = storage.save_file(file.filename, file.content_type, data)

	# Save file metadata
	from backend.app.repositories.files_repo import insert_meta
	meta_id = await insert_meta({
		"filename": file.filename,
		"contentType": file.content_type,
		"size": size,
		"path": path,
		"ownerId": str(user["_id"]) if user else None,
	})

	# Get file metadata
	meta = await get_meta(meta_id)
	url = storage.get_public_url(meta["path"])

	file_ref = {
		"fileId": str(meta["_id"]),
		"filename": meta["filename"],
		"contentType": meta.get("contentType"),
		"size": meta.get("size", 0),
		"path": meta["path"],
		"url": url,
	}

	# Attach file to receiving
	ok = await repo.attach_file(user["restaurantId"], rec_id, file_ref)
	if not ok:
		raise HTTPException(status_code=404, detail="Receiving not found")

	return FileRef(**file_ref)


@router.delete("/receiving/{rec_id}/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def receiving_detach_file(
		rec_id: str,
		file_id: str,
		user: dict = Depends(get_current_user)
):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canUpdate", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	ok = await repo.detach_file(user["restaurantId"], rec_id, file_id)
	if not ok:
		raise HTTPException(status_code=404, detail="Receiving not found")
	return None
