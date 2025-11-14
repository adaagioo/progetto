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
from backend.app.core.rbac_utils import get_resource_access

router = APIRouter()

RESOURCE = "ingredients"


@router.get("/ingredients", response_model=List[Ingredient])
async def list_all(user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access["canView"]:
		raise HTTPException(status_code=403, detail="Forbidden")
	docs = await list_ingredients(user["restaurantId"])
	return docs


@router.get("/ingredients/{ingredient_id}", response_model=Ingredient)
async def get_one(ingredient_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access["canView"]:
		raise HTTPException(status_code=403, detail="Forbidden")
	doc = await get_ingredient(user["restaurantId"], ingredient_id)
	if not doc:
		raise HTTPException(status_code=404, detail="Ingredient not found")
	return doc


@router.post("/ingredients", response_model=Ingredient, status_code=status.HTTP_201_CREATED)
async def create(body: IngredientCreate, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access["canCreate"]:
		raise HTTPException(status_code=403, detail="Forbidden")
	doc = body.model_dump()
	doc["restaurantId"] = user["restaurantId"]
	new_id = await create_ingredient(doc)
	# Reload created
	created = await get_ingredient(user["restaurantId"], new_id)
	return created


@router.patch("/ingredients/{ingredient_id}", response_model=Ingredient)
async def update(ingredient_id: str, body: IngredientUpdate, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access["canUpdate"]:
		raise HTTPException(status_code=403, detail="Forbidden")
	ok = await update_ingredient(user["restaurantId"], ingredient_id,
	                             {k: v for k, v in body.model_dump().items() if v is not None})
	if not ok:
		raise HTTPException(status_code=404, detail="Ingredient not found")
	doc = await get_ingredient(user["restaurantId"], ingredient_id)
	return doc


@router.delete("/ingredients/{ingredient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(ingredient_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access["canDelete"]:
		raise HTTPException(status_code=403, detail="Forbidden")
	ok = await delete_ingredient(user["restaurantId"], ingredient_id)
	if not ok:
		raise HTTPException(status_code=404, detail="Ingredient not found")
	return None


@router.get("/ingredients/{ingredient_id}/price-history", response_model=List[PricePoint])
async def ingredient_price_history(ingredient_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView", True):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	# TODO (af): In the current model, price is associated with Inventory (not Ingredient directly).
	# For consistency with the old endpoint, I interpret ingredient_id = inventoryId.
	# It is possible to map Ingredient -> Inventory first. If so, we can add a lookup.
	rows = await find_receiving_price_history(ingredient_id, limit=200)
	out: List[PricePoint] = []
	for r in rows:
		at = r.get("at")
		out.append(PricePoint(
			date=(at.date() if isinstance(at, (datetime,)) else at),
			unitCost=(r.get("unitCost") if r.get("unitCost") is not None else None),
			receivingId=(str(r.get("receivingId")) if r.get("receivingId") else None),
		))
	return out
