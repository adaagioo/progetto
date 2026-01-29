# backend/app/api/V1/ingredients.py
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from backend.app.schemas.ingredients import Ingredient, IngredientCreate, IngredientUpdate, PricePoint
from backend.app.services.ingredients_service import (
	list_ingredients, get_ingredient, create_ingredient, update_ingredient, delete_ingredient
)
from backend.app.repositories.movements_repo import find_receiving_price_history
from backend.app.deps.auth import get_current_user
from backend.app.core.rbac_policies import get_resource_access

router = APIRouter()

RESOURCE = "ingredients"


@router.get("/ingredients", response_model=List[Ingredient])
async def list_all(user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	docs = await list_ingredients(user["restaurantId"])
	return docs


@router.get("/ingredients/{ingredient_id}", response_model=Ingredient)
async def get_one(ingredient_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	doc = await get_ingredient(user["restaurantId"], ingredient_id)
	if not doc:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingredient not found")
	return doc


@router.post("/ingredients", response_model=Ingredient, status_code=status.HTTP_201_CREATED)
async def create(body: IngredientCreate, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canCreate", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	doc = body.model_dump()
	doc["restaurantId"] = user["restaurantId"]
	new_id = await create_ingredient(doc)
	# Reload created
	created = await get_ingredient(user["restaurantId"], new_id)
	return created


@router.patch("/ingredients/{ingredient_id}", response_model=Ingredient)
@router.put("/ingredients/{ingredient_id}", response_model=Ingredient)
async def update(ingredient_id: str, body: IngredientUpdate, user: dict = Depends(get_current_user)):
	"""Update ingredient (supports both PATCH and PUT for compatibility)"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canUpdate", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	ok = await update_ingredient(user["restaurantId"], ingredient_id,
	                             {k: v for k, v in body.model_dump().items() if v is not None})
	if not ok:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingredient not found")
	doc = await get_ingredient(user["restaurantId"], ingredient_id)
	return doc


@router.delete("/ingredients/{ingredient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(ingredient_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canDelete", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	ok = await delete_ingredient(user["restaurantId"], ingredient_id)
	if not ok:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingredient not found")
	return None


@router.get("/ingredients/{ingredient_id}/price-history")
async def ingredient_price_history(ingredient_id: str, limit: int = 5, user: dict = Depends(get_current_user)):
	"""Get price history for an ingredient from receiving records.

	Returns format expected by frontend: { history: [...] }
	"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	from backend.app.db.mongo import get_db
	db = get_db()

	# Find receiving records that contain this ingredient
	pipeline = [
		{"$match": {"restaurantId": user["restaurantId"]}},
		{"$unwind": "$lines"},
		{"$match": {"lines.ingredientId": ingredient_id}},
		{"$sort": {"date": -1, "createdAt": -1}},
		{"$limit": limit},
		{"$lookup": {
			"from": "suppliers",
			"let": {"supplierId": "$supplierId"},
			"pipeline": [
				{"$match": {"$expr": {"$eq": [{"$toString": "$_id"}, "$$supplierId"]}}}
			],
			"as": "supplier"
		}},
		{"$unwind": {"path": "$supplier", "preserveNullAndEmptyArrays": True}},
		{"$project": {
			"_id": 0,
			"date": {"$ifNull": ["$date", "$createdAt"]},
			"unitPrice": {"$divide": [{"$ifNull": ["$lines.unitPrice", 0]}, 100]},  # Convert from cents
			"qty": "$lines.qty",
			"unit": "$lines.unit",
			"packFormat": "$lines.packFormat",
			"supplierName": "$supplier.name"
		}}
	]

	history = []
	async for doc in db["receiving"].aggregate(pipeline):
		# Handle date serialization
		doc_date = doc.get("date")
		if isinstance(doc_date, datetime):
			doc["date"] = doc_date.isoformat()
		history.append(doc)

	return {"history": history}
