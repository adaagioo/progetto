from __future__ import annotations
from backend.app.db.mongo import get_db


async def ensure_indexes() -> None:
	db = get_db()
	# Users & RBAC
	await db["users"].create_index("email", unique=True)
	await db["rbac_roles"].create_index("roleKey", unique=True)
	# Domain collections
	await db["ingredients"].create_index([("restaurantId", 1), ("name", 1)], unique=False)
	await db["inventory"].create_index([("restaurantId", 1), ("receivingId", 1)], unique=False)
	await db["preparations"].create_index([("restaurantId", 1), ("name", 1)], unique=False)
	await db["recipes"].create_index([("restaurantId", 1), ("name", 1)], unique=False)
