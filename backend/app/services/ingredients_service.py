# backend/app/services/ingredients_service.py
from __future__ import annotations
from typing import List, Optional
from app.repositories.ingredients_repo import find_many, find_one, insert_one, update_one, delete_one

async def list_ingredients(restaurant_id: str) -> List[dict]:
    return await find_many(restaurant_id)

async def get_ingredient(restaurant_id: str, ingredient_id: str) -> Optional[dict]:
    return await find_one(restaurant_id, ingredient_id)

async def create_ingredient(doc: dict) -> str:
    return await insert_one(doc)

async def update_ingredient(restaurant_id: str, ingredient_id: str, patch: dict) -> bool:
    return await update_one(restaurant_id, ingredient_id, patch)

async def delete_ingredient(restaurant_id: str, ingredient_id: str) -> bool:
    return await delete_one(restaurant_id, ingredient_id)
