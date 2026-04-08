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
	# Sales documents have 'revenue' field or we sum from items
	total_sales = 0.0
	try:
		# First try to sum the revenue field directly
		async for s in db["sales"].aggregate([
			{"$match": {"date": {"$gte": datetime.combine(start_date, datetime.min.time()),
			                     "$lte": datetime.combine(end_date, datetime.max.time())}}},
			{"$group": {"_id": None, "sum": {"$sum": {"$ifNull": ["$revenue", 0]}}}},
		]):
			total_sales = float(s.get("sum", 0.0))
	except Exception as e:
		total_sales = 0.0

	# Calculate value usage (inventory consumption + wastage)
	value_usage = 0.0
	wastage_cost = 0.0
	purchases_cost = 0.0
	try:
		# Get wastage cost for the period
		# Wastage items may have 'unitCost' or we need to look it up from ingredients
		async for w in db["wastage"].aggregate([
			{"$match": {"date": {"$gte": datetime.combine(start_date, datetime.min.time()),
			                     "$lte": datetime.combine(end_date, datetime.max.time())}}},
			{"$unwind": "$items"},
			{"$group": {"_id": None, "sum": {"$sum": {"$multiply": [
				{"$ifNull": ["$items.quantity", {"$ifNull": ["$items.qty", 0]}]},
				{"$ifNull": ["$items.unitCost", 0]}
			]}}}},
		]):
			wastage_cost = float(w.get("sum", 0.0))

		# Get receiving (purchases) cost for the period
		# Receiving uses 'date' or 'arrivedAt' field, and items have 'unitPrice'
		async for r in db["receiving"].aggregate([
			{"$match": {"$or": [
				{"date": {"$gte": datetime.combine(start_date, datetime.min.time()),
				          "$lte": datetime.combine(end_date, datetime.max.time())}},
				{"arrivedAt": {"$gte": start_date.isoformat(), "$lte": end_date.isoformat()}}
			]}},
			{"$unwind": "$lines"},
			{"$group": {"_id": None, "sum": {"$sum": {"$multiply": [
				{"$ifNull": ["$lines.qty", 0]},
				{"$ifNull": ["$lines.unitPrice", 0]}
			]}}}},
		]):
			purchases_cost = float(r.get("sum", 0.0))

		# Also try the 'items' field name for receiving (older format)
		if purchases_cost == 0:
			async for r in db["receiving"].aggregate([
				{"$match": {"date": {"$gte": datetime.combine(start_date, datetime.min.time()),
				                     "$lte": datetime.combine(end_date, datetime.max.time())}}},
				{"$unwind": "$items"},
				{"$group": {"_id": None, "sum": {"$sum": {"$multiply": [
					{"$ifNull": ["$items.qty", 0]},
					{"$ifNull": ["$items.unitPrice", 0]}
				]}}}},
			]):
				purchases_cost = float(r.get("sum", 0.0))

		value_usage = purchases_cost + wastage_cost
	except Exception as e:
		value_usage = 0.0

	# Calculate food cost percentage
	food_cost_pct = 0.0
	if total_sales > 0:
		food_cost_pct = (value_usage / total_sales) * 100

	# Calculate low stock count (items where qty < minStockQty from ingredients)
	low_stock_count = 0
	try:
		# Join inventory with ingredients to check against minStockQty
		pipeline = [
			{"$addFields": {"ingredientOid": {"$toObjectId": "$ingredientId"}}},
			{"$lookup": {
				"from": "ingredients",
				"localField": "ingredientOid",
				"foreignField": "_id",
				"as": "ingredient"
			}},
			{"$unwind": {"path": "$ingredient", "preserveNullAndEmptyArrays": True}},
			{"$match": {
				"$expr": {"$lt": ["$qty", {"$ifNull": ["$ingredient.minStockQty", 0]}]}
			}},
			{"$count": "count"}
		]
		async for result in db["inventory"].aggregate(pipeline):
			low_stock_count = result.get("count", 0)
	except Exception:
		low_stock_count = 0

	# Calculate expiring items using batchExpiry (string format YYYY-MM-DD)
	today_str = date.today().isoformat()
	day1_str = (date.today() + timedelta(days=1)).isoformat()
	day2_str = (date.today() + timedelta(days=2)).isoformat()
	day3_str = (date.today() + timedelta(days=3)).isoformat()

	expiring_1day = 0
	expiring_2day = 0
	expiring_3day = 0
	try:
		# Count items expiring within 1 day (today or tomorrow)
		expiring_1day = await db["inventory"].count_documents({
			"batchExpiry": {"$lte": day1_str, "$gte": today_str}
		})
		# Count items expiring in 2 days (day after tomorrow)
		expiring_2day = await db["inventory"].count_documents({
			"batchExpiry": {"$lte": day2_str, "$gt": day1_str}
		})
		# Count items expiring in 3 days
		expiring_3day = await db["inventory"].count_documents({
			"batchExpiry": {"$lte": day3_str, "$gt": day2_str}
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
