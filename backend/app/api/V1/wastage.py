# backend/app/api/V1/wastage.py
from __future__ import annotations
from datetime import date, datetime, timezone
from typing import List, Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status, Query
from backend.app.deps.auth import get_current_user
from backend.app.core.rbac_policies import get_resource_access
from backend.app.schemas.wastage import Wastage, WastageCreate
from backend.app.repositories import wastage_repo as repo
from backend.app.services.inventory_service import deduct_stock_for_wastage
from backend.app.db.mongo import get_db

router = APIRouter()
RESOURCE = "wastage"


async def _enrich_wastage_items(doc: dict) -> dict:
	"""Enrich wastage items with ingredient info"""
	if not doc or "items" not in doc:
		return doc

	db = get_db()
	enriched_items = []

	for item in doc.get("items", []):
		item_id = item.get("inventoryId") or item.get("itemId")
		if not item_id:
			enriched_items.append(item)
			continue

		# Try to find inventory and get ingredientId
		ingredient_id = None
		try:
			inv_doc = await db["inventory"].find_one({"_id": ObjectId(item_id)})
			if inv_doc:
				ingredient_id = inv_doc.get("ingredientId")
		except Exception:
			pass

		# If not found by _id, item_id might be the ingredientId directly
		if not ingredient_id:
			ingredient_id = item_id

		# Look up ingredient name and unit cost
		ingredient_name = None
		ingredient_unit_cost = None
		if ingredient_id:
			try:
				ing_doc = await db["ingredients"].find_one({"_id": ObjectId(ingredient_id)})
				if ing_doc:
					ingredient_name = ing_doc.get("name")
					# Get effectiveUnitCost (includes waste) or fallback to unitCost
					ingredient_unit_cost = ing_doc.get("effectiveUnitCost") or ing_doc.get("unitCost")
			except Exception:
				pass

		# Enrich the item
		item["ingredientId"] = ingredient_id
		item["ingredientName"] = ingredient_name
		item["itemName"] = ingredient_name  # Frontend looks for itemName
		# Set unitCost from ingredient if not already provided
		if not item.get("unitCost") and ingredient_unit_cost:
			item["unitCost"] = ingredient_unit_cost
		enriched_items.append(item)

	doc["items"] = enriched_items

	# Add top-level fields from first item for frontend display
	if enriched_items:
		first = enriched_items[0]
		doc["itemName"] = first.get("itemName")
		doc["qty"] = first.get("quantity") or first.get("qty")
		doc["unit"] = first.get("unit")
		doc["reason"] = first.get("reason")
		# Calculate cost impact if unitCost available
		unit_cost = first.get("unitCost")
		qty_val = first.get("quantity") or first.get("qty") or 0
		if unit_cost:
			doc["costImpact"] = unit_cost * qty_val

	return doc


@router.post("/wastage", response_model=Wastage, status_code=201)
async def wastage_create(payload: WastageCreate, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canCreate"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	items = [i.model_dump(by_alias=True, exclude_none=True) for i in payload.items]
	# Convert date to datetime for MongoDB compatibility
	wastage_date = datetime.combine(payload.date, datetime.min.time())
	wastage_doc = {
		"date": wastage_date,
		"items": items,
		"restaurantId": user["restaurantId"],
		"createdAt": datetime.now(tz=timezone.utc),
		"type": payload.type,
		"notes": payload.notes,
	}
	wid = await repo.insert_one(wastage_doc)

	# Deduct stock with rollback on failure
	try:
		await deduct_stock_for_wastage(items, actor_id=str(user["_id"]))
	except Exception as e:
		# Rollback: delete the wastage record if stock deduction fails
		await repo.delete_one(user["restaurantId"], wid)
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail=f"Failed to deduct stock for wastage: {str(e)}"
		)

	doc = await repo.find_one(user["restaurantId"], wid)
	doc = await _enrich_wastage_items(doc)
	return Wastage(**doc)


@router.get("/wastage", response_model=List[Wastage])
async def wastage_list(
		start: Optional[date] = Query(None),
		end: Optional[date] = Query(None),
		limit: int = 100, skip: int = 0,
		user: dict = Depends(get_current_user),
):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	docs = await repo.find_many(user["restaurantId"], start=start, end=end, limit=limit, skip=skip)
	enriched = [await _enrich_wastage_items(d) for d in docs]
	return [Wastage(**d) for d in enriched]


@router.get("/wastage/{w_id}", response_model=Wastage)
async def wastage_get(w_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	d = await repo.find_one(user["restaurantId"], w_id)
	if not d:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
	d = await _enrich_wastage_items(d)
	return Wastage(**d)


@router.delete("/wastage/{w_id}", status_code=204)
async def wastage_delete(w_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canDelete"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	ok = await repo.delete_one(user["restaurantId"], w_id)
	if not ok:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
	return None
