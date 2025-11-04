# backend/app/services/dependencies_service.py
from __future__ import annotations
from typing import Dict, Any, List
from backend.app.repositories.preparations_repo import lookup_preparation_dependencies
from backend.app.repositories.recipes_repo import lookup_recipe_dependencies


async def get_preparation_dependencies(prep_id: str) -> Dict[str, Any]:
	return await lookup_preparation_dependencies(prep_id)


async def get_recipe_dependencies(recipe_id: str) -> Dict[str, Any]:
	return await lookup_recipe_dependencies(recipe_id)
