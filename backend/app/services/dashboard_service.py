# backend/app/services/dashboard_service.py
from __future__ import annotations
from datetime import date, datetime, timedelta
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
	value_usage = 0.0
	wastage_cost = 0.0
	purchases_cost = 0.0
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

		value_usage = purchases_cost + wastage_cost
	except Exception:
		value_usage = 0.0

	# Calculate food cost percentage
	food_cost_pct = 0.0
	if total_sales > 0:
		food_cost_pct = (value_usage / total_sales) * 100

	# Calculate low stock count (items where qty < minQty)
	low_stock_count = 0
	try:
		low_stock_count = await db["inventory"].count_documents({
			"$expr": {"$lt": ["$qty", {"$ifNull": ["$minQty", 0]}]}
		})
	except Exception:
		low_stock_count = 0

	# Calculate expiring items
	today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
	day1 = today + timedelta(days=1)
	day2 = today + timedelta(days=2)
	day3 = today + timedelta(days=3)

	expiring_1day = 0
	expiring_2day = 0
	expiring_3day = 0
	try:
		expiring_1day = await db["inventory"].count_documents({
			"expiryDate": {"$lte": day1, "$gte": today}
		})
		expiring_2day = await db["inventory"].count_documents({
			"expiryDate": {"$lte": day2, "$gt": day1}
		})
		expiring_3day = await db["inventory"].count_documents({
			"expiryDate": {"$lte": day3, "$gt": day2}
		})
	except Exception:
		pass

	# Calculate last month gross margin (revenue - COGS)
	last_month_gross_margin = round(total_sales - value_usage, 2) if total_sales > 0 else 0.0

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
		},
		# Frontend compatibility fields
		"lowStockCount": low_stock_count,
		"expiring1Day": expiring_1day,
		"expiring2Day": expiring_2day,
		"expiring3Day": expiring_3day,
		"lastMonthGrossMargin": last_month_gross_margin,
		"totalRevenue": round(total_sales, 2),  # Alias for totalSales
		"totalCogs": round(value_usage, 2),  # Alias for valueUsage
	}
