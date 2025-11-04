# backend/app/services/rbac_service.py
from __future__ import annotations
from backend.app.repositories.rbac_repo import find_role, upsert_role


async def get_permissions(role_key: str) -> dict | None:
	doc = await find_role(role_key)
	return doc["permissions"] if doc else None


async def set_permissions(role_key: str, permissions: dict) -> None:
	await upsert_role(role_key, permissions)
