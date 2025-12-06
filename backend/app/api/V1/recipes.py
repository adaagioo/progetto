# backend/app/api/V1/recipes.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List

from backend.app.schemas.dependencies import RecipeDependencies
from backend.app.schemas.recipes import Recipe, RecipeCreate, RecipeUpdate
from backend.app.services.dependencies_service import get_recipe_dependencies
from backend.app.services.recipes_service import (
	list_recipes, get_recipe, create_recipe, update_recipe, delete_recipe
)
from backend.app.deps.auth import get_current_user
from backend.app.core.rbac_policies import get_resource_access

router = APIRouter()
RESOURCE = "recipes"


@router.get("/recipes", response_model=List[Recipe])
async def list_all(user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access["canView"]:
		raise HTTPException(status_code=403, detail="Forbidden")
	return await list_recipes(user["restaurantId"])


@router.get("/recipes/{recipe_id}", response_model=Recipe)
async def get_one(recipe_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access["canView"]:
		raise HTTPException(status_code=403, detail="Forbidden")
	doc = await get_recipe(user["restaurantId"], recipe_id)
	if not doc:
		raise HTTPException(status_code=404, detail="Recipe not found")
	return doc


@router.post("/recipes", response_model=Recipe, status_code=status.HTTP_201_CREATED)
async def create(body: RecipeCreate, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access["canCreate"]:
		raise HTTPException(status_code=403, detail="Forbidden")
	doc = body.model_dump()
	doc["restaurantId"] = user["restaurantId"]
	new_id = await create_recipe(doc)
	created = await get_recipe(user["restaurantId"], new_id)
	return created


@router.put("/recipes/{recipe_id}", response_model=Recipe)
@router.patch("/recipes/{recipe_id}", response_model=Recipe)
async def update(recipe_id: str, body: RecipeUpdate, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access["canUpdate"]:
		raise HTTPException(status_code=403, detail="Forbidden")
	ok = await update_recipe(user["restaurantId"], recipe_id,
	                         {k: v for k, v in body.model_dump().items() if v is not None})
	if not ok:
		raise HTTPException(status_code=404, detail="Recipe not found")
	return await get_recipe(user["restaurantId"], recipe_id)


@router.delete("/recipes/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(recipe_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access["canDelete"]:
		raise HTTPException(status_code=403, detail="Forbidden")
	ok = await delete_recipe(user["restaurantId"], recipe_id)
	if not ok:
		raise HTTPException(status_code=404, detail="Recipe not found")
	return None


@router.get("/recipes/{recipe_id}/dependencies", response_model=RecipeDependencies)
async def recipe_dependencies(recipe_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, "recipes")
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	deps = await get_recipe_dependencies(recipe_id)
	return RecipeDependencies(**deps)
