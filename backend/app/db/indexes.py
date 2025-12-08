from __future__ import annotations
from backend.app.db.mongo import get_db


async def ensure_indexes() -> None:
	db = get_db()

	# Users & RBAC
	await db["users"].create_index("email", unique=True)
	await db["rbac_roles"].create_index("roleKey", unique=True)

	# Domain collections with restaurantId
	await db["ingredients"].create_index([("restaurantId", 1), ("name", 1)], unique=False)
	await db["preparations"].create_index([("restaurantId", 1), ("name", 1)], unique=False)
	await db["recipes"].create_index([("restaurantId", 1), ("name", 1)], unique=False)
	await db["suppliers"].create_index("restaurantId")

	# Inventory & movements
	await db["inventory"].create_index([("restaurantId", 1), ("receivingId", 1)], unique=False)
	await db["inventory"].create_index([("restaurantId", 1), ("ingredientId", 1)], unique=False)
	await db["inventory"].create_index([("restaurantId", 1), ("expiryDate", 1)], unique=False)
	await db["inventory_movements"].create_index([("inventoryId", 1), ("kind", 1)], unique=False)
	await db["inventory_movements"].create_index("restaurantId")

	# Sales & wastage (for P&L and date-range queries)
	await db["sales"].create_index([("restaurantId", 1), ("date", 1)], unique=False)
	await db["wastage"].create_index([("restaurantId", 1), ("date", 1)], unique=False)

	# Receiving
	await db["receiving"].create_index([("restaurantId", 1), ("date", 1)], unique=False)

	# Menus
	await db["menus"].create_index("restaurantId")
	await db["menu_items"].create_index("menuId")

	# TTL indexes for temporary data (expire after specified time)
	await db["password_reset"].create_index("expiresAt", expireAfterSeconds=0)
	await db["login_attempts"].create_index("timestamp", expireAfterSeconds=3600)  # 1 hour
