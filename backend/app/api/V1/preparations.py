# backend/app/api/V1/preparations.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List

from backend.app.schemas.dependencies import PreparationDependencies
from backend.app.schemas.preparations import Preparation, PreparationCreate, PreparationUpdate
from backend.app.services.dependencies_service import get_preparation_dependencies
from backend.app.services.preparations_service import (
	list_preparations, get_preparation, create_preparation, update_preparation, delete_preparation
)
from backend.app.deps.auth import get_current_user
from backend.app.core.rbac_utils import get_resource_access

router = APIRouter()
RESOURCE = "preparations"


@router.get("/preparations", response_model=List[Preparation])
async def list_all(user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access["canView"]:
		raise HTTPException(status_code=403, detail="Forbidden")
	return await list_preparations(user["restaurantId"])


@router.get("/preparations/{prep_id}", response_model=Preparation)
async def get_one(prep_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access["canView"]:
		raise HTTPException(status_code=403, detail="Forbidden")
	doc = await get_preparation(user["restaurantId"], prep_id)
	if not doc:
		raise HTTPException(status_code=404, detail="Preparation not found")
	return doc


@router.post("/preparations", response_model=Preparation, status_code=status.HTTP_201_CREATED)
async def create(body: PreparationCreate, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access["canCreate"]:
		raise HTTPException(status_code=403, detail="Forbidden")
	doc = body.model_dump()
	doc["restaurantId"] = user["restaurantId"]
	new_id = await create_preparation(doc)
	created = await get_preparation(user["restaurantId"], new_id)
	return created


@router.patch("/preparations/{prep_id}", response_model=Preparation)
async def update(prep_id: str, body: PreparationUpdate, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access["canUpdate"]:
		raise HTTPException(status_code=403, detail="Forbidden")
	ok = await update_preparation(user["restaurantId"], prep_id,
	                              {k: v for k, v in body.model_dump().items() if v is not None})
	if not ok:
		raise HTTPException(status_code=404, detail="Preparation not found")
	return await get_preparation(user["restaurantId"], prep_id)


@router.delete("/preparations/{prep_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(prep_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access["canDelete"]:
		raise HTTPException(status_code=403, detail="Forbidden")
	ok = await delete_preparation(user["restaurantId"], prep_id)
	if not ok:
		raise HTTPException(status_code=404, detail="Preparation not found")
	return None


@router.get("/preparations/{prep_id}/dependencies", response_model=PreparationDependencies)
async def preparation_dependencies(prep_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, "preparations")
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	deps = await get_preparation_dependencies(prep_id)
	return PreparationDependencies(**deps)
