#!/usr/bin/env python3
"""
Seed test data for Phase 4 UAT:
- Historical sales data for forecasting
- Expiring inventory batches for alerts
- Multiple suppliers for supplier switching
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta, timezone

BACKEND_URL = "https://ristobrain-1.preview.emergentagent.com/api"

async def seed_phase4_uat_data():
    """Seed comprehensive test data for Phase 4 UAT"""
    
    async with aiohttp.ClientSession() as session:
        # Login as admin
        login_data = {"email": "admin@test.com", "password": "admin123"}
        async with session.post(f"{BACKEND_URL}/auth/login", json=login_data) as resp:
            if resp.status != 200:
                print(f"❌ Login failed: {resp.status}")
                return
            auth_data = await resp.json()
            token = auth_data["access_token"]
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        print("🔐 Authenticated as admin")
        
        # 1. Create additional suppliers for supplier switching test
        print("\n📦 Creating multiple suppliers...")
        suppliers = [
            {"name": "Metro Cash & Carry", "contacts": "metro@example.com", "notes": "Preferred supplier for dry goods"},
            {"name": "Sysco Italia", "contacts": "sysco@example.com", "notes": "Fresh produce specialist"},
            {"name": "Chef Store", "contacts": "chef@example.com", "notes": "Professional equipment & ingredients"}
        ]
        
        supplier_ids = []
        for supplier_data in suppliers:
            async with session.post(f"{BACKEND_URL}/suppliers", json=supplier_data, headers=headers) as resp:
                if resp.status == 200:
                    supplier = await resp.json()
                    supplier_ids.append(supplier["id"])
                    print(f"   ✅ Created supplier: {supplier_data['name']}")
        
        # 2. Get existing ingredients
        print("\n🥬 Fetching ingredients...")
        async with session.get(f"{BACKEND_URL}/ingredients", headers=headers) as resp:
            ingredients = await resp.json() if resp.status == 200 else []
        
        if not ingredients:
            print("   ⚠️ No ingredients found, creating test ingredients...")
            # Create test ingredients with pack sizes
            test_ingredients = [
                {
                    "name": "Flour 00",
                    "unit": "kg",
                    "packSize": 25.0,
                    "packCost": 62500,  # €25.00 in minor units
                    "wastePct": 5.0,
                    "minStockQty": 10.0,
                    "allergens": ["gluten"],
                    "category": "food"
                },
                {
                    "name": "Fresh Tomatoes",
                    "unit": "kg",
                    "packSize": 5.0,
                    "packCost": 1750,  # €17.50 in minor units
                    "wastePct": 15.0,
                    "minStockQty": 3.0,
                    "allergens": [],
                    "category": "food",
                    "shelfLife": {"value": 5, "unit": "days"}
                },
                {
                    "name": "Mozzarella di Bufala",
                    "unit": "kg",
                    "packSize": 1.0,
                    "packCost": 1800,  # €18.00 in minor units
                    "wastePct": 8.0,
                    "minStockQty": 2.0,
                    "allergens": ["dairy"],
                    "category": "food",
                    "shelfLife": {"value": 7, "unit": "days"}
                }
            ]
            
            for ing_data in test_ingredients:
                async with session.post(f"{BACKEND_URL}/ingredients", json=ing_data, headers=headers) as resp:
                    if resp.status == 200:
                        ingredient = await resp.json()
                        ingredients.append(ingredient)
                        print(f"   ✅ Created ingredient: {ing_data['name']}")
        
        print(f"   Found {len(ingredients)} ingredients")
        
        # 3. Create expiring inventory batches
        print("\n⏰ Creating expiring inventory batches...")
        today = datetime.now(timezone.utc)
        tomorrow = today + timedelta(days=1)
        day_after = today + timedelta(days=2)
        
        expiring_inventory = [
            {
                "ingredientId": ingredients[1]["id"] if len(ingredients) > 1 else ingredients[0]["id"],
                "qty": 3.5,
                "unit": "kg",
                "countType": "opening",
                "batchExpiry": tomorrow.strftime("%Y-%m-%d"),
                "location": "Main Fridge"
            },
            {
                "ingredientId": ingredients[2]["id"] if len(ingredients) > 2 else ingredients[0]["id"],
                "qty": 1.2,
                "unit": "kg",
                "countType": "opening",
                "batchExpiry": day_after.strftime("%Y-%m-%d"),
                "location": "Cheese Storage"
            }
        ]
        
        for inv_data in expiring_inventory:
            async with session.post(f"{BACKEND_URL}/inventory", json=inv_data, headers=headers) as resp:
                if resp.status == 200:
                    inventory = await resp.json()
                    print(f"   ✅ Created expiring batch: {inv_data['qty']} {inv_data['unit']} expires {inv_data['batchExpiry']}")
        
        # 4. Get existing preparations and recipes
        print("\n🍕 Fetching preparations and recipes...")
        async with session.get(f"{BACKEND_URL}/preparations", headers=headers) as resp:
            preparations = await resp.json() if resp.status == 200 else []
        
        async with session.get(f"{BACKEND_URL}/recipes", headers=headers) as resp:
            recipes = await resp.json() if resp.status == 200 else []
        
        print(f"   Found {len(preparations)} preparations, {len(recipes)} recipes")
        
        # 5. Create historical sales data (last 4 weeks, same weekday)
        if recipes:
            print("\n📊 Creating historical sales data...")
            target_date = datetime.now(timezone.utc) + timedelta(days=1)  # Tomorrow
            weekday = target_date.weekday()
            
            # Create sales for last 4 weeks on same weekday
            for week_offset in range(1, 5):
                past_date = target_date - timedelta(weeks=week_offset)
                
                sales_data = {
                    "date": past_date.strftime("%Y-%m-%d"),
                    "lines": [
                        {
                            "recipeId": recipes[0]["id"],
                            "qty": 10 + week_offset  # Varying quantities for trend
                        }
                    ],
                    "revenue": (1200 + week_offset * 100),  # €12-15 in minor units
                    "notes": f"Historical sales for forecast testing - Week {week_offset}"
                }
                
                async with session.post(f"{BACKEND_URL}/sales", json=sales_data, headers=headers) as resp:
                    if resp.status == 200:
                        print(f"   ✅ Created sales record: {past_date.strftime('%Y-%m-%d')} - {sales_data['lines'][0]['qty']} portions")
        
        # 6. Create low stock inventory for order list testing
        print("\n📉 Creating low stock inventory...")
        if len(ingredients) >= 2:
            low_stock_data = {
                "ingredientId": ingredients[0]["id"],
                "qty": 2.0,  # Below minStockQty
                "unit": "kg",
                "countType": "opening",
                "location": "Dry Storage"
            }
            
            async with session.post(f"{BACKEND_URL}/inventory", json=low_stock_data, headers=headers) as resp:
                if resp.status == 200:
                    print(f"   ✅ Created low stock inventory: 2.0 kg (min: {ingredients[0].get('minStockQty', 10)} kg)")
        
        print("\n✅ Phase 4 UAT data seeding complete!")
        print("\n📋 Summary:")
        print(f"   - {len(supplier_ids)} suppliers created")
        print(f"   - {len(expiring_inventory)} expiring batches created")
        print(f"   - 4 weeks of historical sales created")
        print(f"   - Low stock inventory created")

if __name__ == "__main__":
    asyncio.run(seed_phase4_uat_data())
