# backend/app/services/dashboard_service.py
from __future__ import annotations
from datetime import date, timedelta
from backend.app.db.mongo import get_db


async def get_kpis(start_date: date = None, end_date: date = None) -> dict:
	"""
	Get key performance indicators for the dashboard.

	Args:
		start_date: Optional start date for calculations (defaults to 30 days ago)
		end_date: Optional end date for calculations (defaults to today)

	Returns:
		Dictionary with KPIs including real food cost percentage
	"""
	db = get_db()

	async def count(col: str) -> int:
		try:
			return await db[col].count_documents({})
		except Exception:
			return 0

	# Set default date range (last 30 days)
	if not end_date:
		end_date = date.today()
	if not start_date:
		start_date = end_date - timedelta(days=30)

	# Calculate total sales revenue
	total_sales = 0.0
	try:
		async for s in db["sales"].aggregate([
			{"$match": {"date": {"$gte": start_date, "$lte": end_date}}},
			{"$unwind": "$items"},
			{"$group": {"_id": None, "sum": {"$sum": {"$multiply": ["$items.quantity", "$items.price"]}}}},
		]):
			total_sales = float(s.get("sum", 0.0))
	except Exception:
		total_sales = 0.0

	# Calculate value usage (inventory consumption + wastage)
	# Value usage = Beginning inventory + Purchases - Ending inventory + Wastage
	value_usage = 0.0
	try:
		# Get wastage cost for the period
		async for w in db["wastage"].aggregate([
			{"$match": {"date": {"$gte": start_date, "$lte": end_date}}},
			{"$unwind": "$items"},
			{"$group": {"_id": None, "sum": {"$sum": {"$multiply": ["$items.quantity", "$items.unitCost"]}}}},
		]):
			wastage_cost = float(w.get("sum", 0.0))

		# Get receiving (purchases) cost for the period
		async for r in db["receiving"].aggregate([
			{"$match": {"deliveryDate": {"$gte": start_date, "$lte": end_date}}},
			{"$unwind": "$items"},
			{"$group": {"_id": None, "sum": {"$sum": {"$multiply": ["$items.quantity", "$items.unitCost"]}}}},
		]):
			purchases_cost = float(r.get("sum", 0.0))

		# Simplified: value_usage ≈ purchases + wastage
		# (More accurate would require beginning/ending inventory snapshots)
		value_usage = purchases_cost + wastage_cost
	except Exception:
		value_usage = 0.0

	# Calculate food cost percentage
	food_cost_pct = 0.0
	if total_sales > 0:
		food_cost_pct = (value_usage / total_sales) * 100

	return {
		"totalRecipes": await count("recipes"),
		"totalIngredients": await count("ingredients"),
		"totalInventoryItems": await count("inventory"),
		"totalSuppliers": await count("suppliers"),
		"totalSalesOrders": await count("sales"),
		"totalSales": round(total_sales, 2),
		"valueUsage": round(value_usage, 2),
		"foodCostPct": round(food_cost_pct, 2),
		"dateRange": {
			"start": start_date.isoformat(),
			"end": end_date.isoformat()
		}
	}
