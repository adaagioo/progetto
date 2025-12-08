# backend/app/api/V1/dependencies.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException, status, Depends
from backend.app.deps.auth import get_current_user
from backend.app.core.rbac_policies import get_resource_access
from backend.app.repositories.preparations_repo import lookup_preparation_dependencies
from backend.app.repositories.recipes_repo import lookup_recipe_dependencies
from backend.app.repositories.inventory_repo import lookup_inventory_dependencies

router = APIRouter()
RESOURCE = "dependencies"


@router.get("/dependencies/recipe/{recipe_id}")
async def recipe_dependencies(recipe_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	data = await lookup_recipe_dependencies(recipe_id)
	if not data:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
	return data


@router.get("/dependencies/preparation/{prep_id}")
async def preparation_dependencies(prep_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	data = await lookup_preparation_dependencies(prep_id)
	if not data:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
	return data


@router.get("/dependencies/inventory/{inventory_id}")
async def inventory_dependencies(inventory_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	data = await lookup_inventory_dependencies(inventory_id)
	if not data:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
	return data
