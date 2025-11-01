# backend/app/services/recipes_service.py
from __future__ import annotations
from typing import List, Optional
from app.repositories.recipes_repo import find_many, find_one, insert_one, update_one, delete_one

async def list_recipes(restaurant_id: str) -> List[dict]:
    return await find_many(restaurant_id)

async def get_recipe(restaurant_id: str, recipe_id: str) -> Optional[dict]:
    return await find_one(restaurant_id, recipe_id)

async def create_recipe(doc: dict) -> str:
    return await insert_one(doc)

async def update_recipe(restaurant_id: str, recipe_id: str, patch: dict) -> bool:
    return await update_one(restaurant_id, recipe_id, patch)

async def delete_recipe(restaurant_id: str, recipe_id: str) -> bool:
    return await delete_one(restaurant_id, recipe_id)
