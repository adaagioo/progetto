# backend/app/api/V1/menu.py
from __future__ import annotations
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from backend.app.deps.auth import get_current_user
from backend.app.core.rbac_policies import get_resource_access
from backend.app.schemas.menu import Menu, MenuCreate, MenuUpdate, MenuItem, MenuItemCreate, MenuItemUpdate
from backend.app.repositories import menu_repo as repo
from backend.app.services.menu_service import populate_menu_item_data
from backend.app.db.mongo import get_db

router = APIRouter()
RESOURCE = "menu"


# ========== MENU ENDPOINTS ==========

@router.post("/menu", response_model=Menu, status_code=201)
async def create_menu(payload: MenuCreate, user: dict = Depends(get_current_user)):
	"""Create a new menu"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canCreate"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	# Check for overlapping active menus
	if payload.isActive:
		existing_active = await repo.get_active_menu(user["restaurantId"])
		if existing_active:
			raise HTTPException(
				status_code=400,
				detail="Another active menu already exists. Deactivate it first or set this menu as inactive."
			)

	menu_id = await repo.create_menu(
		user["restaurantId"],
		payload.name,
		payload.description,
		payload.effectiveFrom,
		payload.effectiveTo,
		payload.isActive
	)

	menu = await repo.get_menu(menu_id, user["restaurantId"])
	return Menu(**menu)


@router.get("/menu", response_model=List[Menu])
async def list_menus(user: dict = Depends(get_current_user)):
	"""Get all menus for the restaurant"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	menus = await repo.list_menus(user["restaurantId"])
	return [Menu(**m) for m in menus]


@router.get("/menu/current")
async def get_current_menu(user: dict = Depends(get_current_user)):
	"""Get the currently active menu with all items"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	# Find active menu
	menu = await repo.get_active_menu(user["restaurantId"])

	if not menu:
		return {"menu": None, "items": []}

	# Get all menu items
	menu_items = await repo.list_menu_items(menu["id"])

	# Populate each menu item with data from referenced entities
	populated_items = []
	for item in menu_items:
		populated_item = await populate_menu_item_data(item)
		populated_items.append(populated_item)

	return {
		"menu": Menu(**menu),
		"items": populated_items
	}


@router.get("/menu/{menu_id}", response_model=Menu)
async def get_menu(menu_id: str, user: dict = Depends(get_current_user)):
	"""Get a specific menu"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	menu = await repo.get_menu(menu_id, user["restaurantId"])

	if not menu:
		raise HTTPException(status_code=404, detail="Menu not found")

	return Menu(**menu)


@router.patch("/menu/{menu_id}", response_model=Menu)
async def update_menu(menu_id: str, payload: MenuUpdate, user: dict = Depends(get_current_user)):
	"""Update a menu"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canUpdate"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	# Check if menu exists
	existing = await repo.get_menu(menu_id, user["restaurantId"])
	if not existing:
		raise HTTPException(status_code=404, detail="Menu not found")

	# If activating this menu, deactivate others
	if payload.isActive is True and not existing.get("isActive"):
		await repo.deactivate_all_menus(user["restaurantId"])

	# Build update dict
	update_data = {}
	if payload.name is not None:
		update_data["name"] = payload.name
	if payload.description is not None:
		update_data["description"] = payload.description
	if payload.effectiveFrom is not None:
		update_data["effectiveFrom"] = payload.effectiveFrom
	if payload.effectiveTo is not None:
		update_data["effectiveTo"] = payload.effectiveTo
	if payload.isActive is not None:
		update_data["isActive"] = payload.isActive

	await repo.update_menu(menu_id, user["restaurantId"], update_data)

	# Fetch and return updated menu
	updated = await repo.get_menu(menu_id, user["restaurantId"])
	return Menu(**updated)


@router.delete("/menu/{menu_id}")
async def delete_menu(menu_id: str, user: dict = Depends(get_current_user)):
	"""Delete a menu and all its items"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canDelete"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	# Check if menu exists
	menu = await repo.get_menu(menu_id, user["restaurantId"])
	if not menu:
		raise HTTPException(status_code=404, detail="Menu not found")

	# Delete all menu items first
	await repo.delete_all_menu_items(menu_id)

	# Delete menu
	await repo.delete_menu(menu_id, user["restaurantId"])

	return {"message": "Menu deleted"}


# ========== MENU ITEM ENDPOINTS ==========

@router.post("/menu/{menu_id}/items", response_model=List[MenuItem])
async def add_menu_items(menu_id: str, items: List[MenuItemCreate], user: dict = Depends(get_current_user)):
	"""Add multiple items to a menu (batch operation)"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canCreate"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	# Check if menu exists and belongs to restaurant
	menu = await repo.get_menu(menu_id, user["restaurantId"])
	if not menu:
		raise HTTPException(status_code=404, detail="Menu not found")

	db = get_db()
	created_items = []

	for item in items:
		# Validate refType
		if item.refType not in ["ingredient", "preparation", "recipe"]:
			raise HTTPException(status_code=400, detail=f"Invalid refType: {item.refType}")

		# Validate that referenced entity exists
		collection_map = {
			"ingredient": "ingredients",
			"preparation": "preparations",
			"recipe": "recipes"
		}
		collection_name = collection_map[item.refType]
		ref_entity = await db[collection_name].find_one(
			{"id": item.refId, "restaurantId": user["restaurantId"]}
		)
		if not ref_entity:
			raise HTTPException(status_code=404, detail=f"{item.refType.capitalize()} {item.refId} not found")

		# Check for duplicates
		existing = await repo.find_duplicate_menu_item(menu_id, item.refType, item.refId)
		if existing:
			# Skip duplicate
			continue

		# Create menu item
		item_id = await repo.create_menu_item(
			menu_id,
			item.refType,
			item.refId,
			item.displayName,
			item.price,
			item.tags or [],
			item.isActive
		)

		# Fetch and populate item data
		menu_item = await repo.get_menu_item(item_id, menu_id)
		populated_item = await populate_menu_item_data(menu_item)
		created_items.append(MenuItem(**populated_item))

	return created_items


@router.get("/menu/{menu_id}/items")
async def get_menu_items(menu_id: str, user: dict = Depends(get_current_user)):
	"""Get all items for a menu"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	# Check if menu exists
	menu = await repo.get_menu(menu_id, user["restaurantId"])
	if not menu:
		raise HTTPException(status_code=404, detail="Menu not found")

	# Get menu items
	menu_items = await repo.list_menu_items(menu_id)

	# Populate each item
	populated_items = []
	for item in menu_items:
		populated_item = await populate_menu_item_data(item)
		populated_items.append(populated_item)

	return populated_items


@router.patch("/menu/{menu_id}/items/{item_id}")
async def update_menu_item(menu_id: str, item_id: str, payload: MenuItemUpdate, user: dict = Depends(get_current_user)):
	"""Update a menu item (toggle isActive, update price, tags)"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canUpdate"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	# Check if menu item exists
	existing = await repo.get_menu_item(item_id, menu_id)
	if not existing:
		raise HTTPException(status_code=404, detail="Menu item not found")

	# Build update dict
	update_data = {}
	if payload.displayName is not None:
		update_data["displayName"] = payload.displayName
	if payload.price is not None:
		update_data["price"] = payload.price
	if payload.tags is not None:
		update_data["tags"] = payload.tags
	if payload.isActive is not None:
		update_data["isActive"] = payload.isActive

	await repo.update_menu_item(item_id, menu_id, update_data)

	# Fetch and return updated item
	updated = await repo.get_menu_item(item_id, menu_id)
	populated_item = await populate_menu_item_data(updated)

	return populated_item


@router.delete("/menu/{menu_id}/items/{item_id}")
async def delete_menu_item(menu_id: str, item_id: str, user: dict = Depends(get_current_user)):
	"""Delete a menu item"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canDelete"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	# Delete menu item
	deleted = await repo.delete_menu_item(item_id, menu_id)
	if not deleted:
		raise HTTPException(status_code=404, detail="Menu item not found")

	return {"message": "Menu item deleted"}
