# backend/app/services/dashboard_service.py
from __future__ import annotations
from backend.app.db.mongo import get_db


async def get_kpis() -> dict:
	db = get_db()

	async def count(col: str) -> int:
		try:
			return await db[col].count_documents({})
		except Exception:
			return 0

	return {
		"totalRecipes": await count("recipes"),
		"totalIngredients": await count("ingredients"),
		"totalInventoryItems": await count("inventory"),
		"totalSuppliers": await count("suppliers"),
		"totalSalesOrders": await count("sales"),
	}
