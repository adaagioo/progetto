# backend/app/services/inventory_service.py
from __future__ import annotations
from typing import List, Optional
from backend.app.repositories.inventory_repo import find_all, find_by_id, insert_one, delete_by_receiving


async def list_inventory(restaurant_id: str) -> List[dict]:
	return await find_all(restaurant_id)


async def get_inventory(restaurant_id: str, inv_id: str) -> Optional[dict]:
	return await find_by_id(restaurant_id, inv_id)


async def create_inventory(doc: dict) -> str:
	return await insert_one(doc)


async def delete_inventory_by_receiving(restaurant_id: str, receiving_id: str) -> int:
	return await delete_by_receiving(restaurant_id, receiving_id)
