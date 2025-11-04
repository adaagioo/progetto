# backend/app/repositories/rbac_repo.py
from __future__ import annotations
from typing import Optional, Any
from backend.app.db.mongo import get_db


def _col():
	return get_db()["rbac_roles"]


async def find_role(role_key: str) -> Optional[dict[str, Any]]:
	return await _col().find_one({"roleKey": role_key})


async def upsert_role(role_key: str, permissions: dict) -> None:
	await _col().update_one(
		{"roleKey": role_key},
		{"$set": {"roleKey": role_key, "permissions": permissions}},
		upsert=True,
	)
