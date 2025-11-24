# backend/app/services/preparations_service.py
from __future__ import annotations
from typing import List, Optional
from backend.app.repositories.preparations_repo import find_many, find_one, insert_one, update_one, delete_one


async def list_preparations(restaurant_id: str) -> List[dict]:
	return await find_many(restaurant_id)


async def get_preparation(restaurant_id: str, prep_id: str) -> Optional[dict]:
	return await find_one(restaurant_id, prep_id)


async def create_preparation(doc: dict) -> str:
	return await insert_one(doc)


async def update_preparation(restaurant_id: str, prep_id: str, patch: dict) -> bool:
	return await update_one(restaurant_id, prep_id, patch)


async def delete_preparation(restaurant_id: str, prep_id: str) -> bool:
	return await delete_one(restaurant_id, prep_id)
