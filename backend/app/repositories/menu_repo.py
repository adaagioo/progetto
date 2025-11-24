# backend/app/repositories/menu_repo.py
from __future__ import annotations
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid
from backend.app.db.mongo import get_db


def _menus_col():
	return get_db()["menus"]


def _menu_items_col():
	return get_db()["menu_items"]


async def create_menu(restaurant_id: str, name: str, description: Optional[str],
                     effective_from: str, effective_to: Optional[str], is_active: bool) -> str:
	"""Create a new menu"""
	menu_id = str(uuid.uuid4())
	doc = {
		"id": menu_id,
		"restaurantId": restaurant_id,
		"name": name,
		"description": description,
		"effectiveFrom": effective_from,
		"effectiveTo": effective_to,
		"isActive": is_active,
		"createdAt": datetime.now(timezone.utc).isoformat(),
		"updatedAt": None
	}
	await _menus_col().insert_one(doc)
	return menu_id


async def get_menu(menu_id: str, restaurant_id: str) -> Optional[Dict[str, Any]]:
	"""Get a menu by ID"""
	return await _menus_col().find_one({"id": menu_id, "restaurantId": restaurant_id}, {"_id": 0})


async def list_menus(restaurant_id: str, limit: int = 1000) -> List[Dict[str, Any]]:
	"""List all menus for a restaurant"""
	cursor = _menus_col().find(
		{"restaurantId": restaurant_id},
		{"_id": 0}
	).sort("effectiveFrom", -1).limit(limit)
	return await cursor.to_list(length=limit)


async def get_active_menu(restaurant_id: str) -> Optional[Dict[str, Any]]:
	"""Get the currently active menu"""
	return await _menus_col().find_one(
		{"restaurantId": restaurant_id, "isActive": True},
		{"_id": 0}
	)


async def update_menu(menu_id: str, restaurant_id: str, update_data: Dict[str, Any]) -> bool:
	"""Update a menu"""
	update_data["updatedAt"] = datetime.now(timezone.utc).isoformat()
	result = await _menus_col().update_one(
		{"id": menu_id, "restaurantId": restaurant_id},
		{"$set": update_data}
	)
	return result.matched_count == 1


async def deactivate_all_menus(restaurant_id: str) -> int:
	"""Deactivate all menus for a restaurant"""
	result = await _menus_col().update_many(
		{"restaurantId": restaurant_id, "isActive": True},
		{"$set": {"isActive": False, "updatedAt": datetime.now(timezone.utc).isoformat()}}
	)
	return result.modified_count


async def delete_menu(menu_id: str, restaurant_id: str) -> bool:
	"""Delete a menu"""
	result = await _menus_col().delete_one({"id": menu_id, "restaurantId": restaurant_id})
	return result.deleted_count == 1


# ========== MENU ITEM OPERATIONS ==========

async def create_menu_item(menu_id: str, ref_type: str, ref_id: str,
                          display_name: Optional[str], price: Optional[float],
                          tags: List[str], is_active: bool) -> str:
	"""Create a menu item"""
	item_id = str(uuid.uuid4())
	doc = {
		"id": item_id,
		"menuId": menu_id,
		"refType": ref_type,
		"refId": ref_id,
		"displayName": display_name,
		"price": price,
		"tags": tags or [],
		"isActive": is_active,
		"createdAt": datetime.now(timezone.utc).isoformat(),
		"updatedAt": None
	}
	await _menu_items_col().insert_one(doc)
	return item_id


async def get_menu_item(item_id: str, menu_id: str) -> Optional[Dict[str, Any]]:
	"""Get a menu item by ID"""
	return await _menu_items_col().find_one({"id": item_id, "menuId": menu_id}, {"_id": 0})


async def list_menu_items(menu_id: str, limit: int = 1000) -> List[Dict[str, Any]]:
	"""List all items for a menu"""
	cursor = _menu_items_col().find({"menuId": menu_id}, {"_id": 0}).limit(limit)
	return await cursor.to_list(length=limit)


async def find_duplicate_menu_item(menu_id: str, ref_type: str, ref_id: str) -> Optional[Dict[str, Any]]:
	"""Check if a menu item already exists"""
	return await _menu_items_col().find_one({
		"menuId": menu_id,
		"refType": ref_type,
		"refId": ref_id
	}, {"_id": 0})


async def update_menu_item(item_id: str, menu_id: str, update_data: Dict[str, Any]) -> bool:
	"""Update a menu item"""
	update_data["updatedAt"] = datetime.now(timezone.utc).isoformat()
	result = await _menu_items_col().update_one(
		{"id": item_id, "menuId": menu_id},
		{"$set": update_data}
	)
	return result.matched_count == 1


async def delete_menu_item(item_id: str, menu_id: str) -> bool:
	"""Delete a menu item"""
	result = await _menu_items_col().delete_one({"id": item_id, "menuId": menu_id})
	return result.deleted_count == 1


async def delete_all_menu_items(menu_id: str) -> int:
	"""Delete all items for a menu"""
	result = await _menu_items_col().delete_many({"menuId": menu_id})
	return result.deleted_count
