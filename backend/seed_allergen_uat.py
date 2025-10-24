#!/usr/bin/env python3
"""
Seed UAT data for allergen taxonomy testing
Creates ingredients with various allergen combinations, preparations, and recipes
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta

BACKEND_URL = "https://menuflow-8.preview.emergentagent.com/api"
ADMIN_CREDENTIALS = {"email": "admin@test.com", "password": "admin123"}

async def seed_allergen_uat_data():
    """Seed comprehensive allergen test data"""
    async with aiohttp.ClientSession() as session:
        # Login as admin
        print("=" * 80)
        print("ALLERGEN UAT DATA SEEDING")
        print("=" * 80)
        
        async with session.post(
            f"{BACKEND_URL}/auth/login",
            json=ADMIN_CREDENTIALS,
            headers={"Content-Type": "application/json"}
        ) as response:
            if response.status != 200:
                print(f"❌ Login failed: {response.status}")
                return
            
            auth_data = await response.json()
            auth_headers = {
                "Authorization": f"Bearer {auth_data['access_token']}",
                "Content-Type": "application/json"
            }
            print("✅ Authenticated as admin")
        
        # Create ingredients with diverse allergen combinations
        ingredients = [
            {
                "name": "All-Purpose Flour",
                "unit": "kg",
                "packSize": 25.0,
                "packCost": 15.00,
                "minStockQty": 10.0,
                "category": "food",
                "wastePct": 5.0,
                "allergens": ["GLUTEN"],
                "otherAllergens": [],
                "shelfLife": {"value": 180, "unit": "days"}
            },
            {
                "name": "Fresh Milk",
                "unit": "ml",
                "packSize": 1000.0,
                "packCost": 1.50,
                "minStockQty": 5000.0,
                "category": "food",
                "wastePct": 10.0,
                "allergens": ["DAIRY"],
                "otherAllergens": [],
                "shelfLife": {"value": 7, "unit": "days"}
            },
            {
                "name": "Shrimp (Fresh)",
                "unit": "kg",
                "packSize": 2.0,
                "packCost": 25.00,
                "minStockQty": 2.0,
                "category": "food",
                "wastePct": 20.0,
                "allergens": ["CRUSTACEANS"],
                "otherAllergens": [],
                "shelfLife": {"value": 2, "unit": "days"}
            },
            {
                "name": "Mixed Nuts (Almonds, Cashews)",
                "unit": "kg",
                "packSize": 1.0,
                "packCost": 12.00,
                "minStockQty": 2.0,
                "category": "food",
                "wastePct": 5.0,
                "allergens": ["TREE_NUTS"],
                "otherAllergens": [],
                "shelfLife": {"value": 90, "unit": "days"}
            },
            {
                "name": "Eggs (Free Range)",
                "unit": "pcs",
                "packSize": 12.0,
                "packCost": 4.00,
                "minStockQty": 24.0,
                "category": "food",
                "wastePct": 8.0,
                "allergens": ["EGGS"],
                "otherAllergens": [],
                "shelfLife": {"value": 14, "unit": "days"}
            },
            {
                "name": "White Truffle Oil",
                "unit": "ml",
                "packSize": 250.0,
                "packCost": 45.00,
                "minStockQty": 250.0,
                "category": "food",
                "wastePct": 2.0,
                "allergens": [],
                "otherAllergens": ["White Truffle Extract", "Artificial Truffle Flavoring"],
                "shelfLife": {"value": 365, "unit": "days"}
            },
            {
                "name": "Soy Sauce (Premium)",
                "unit": "ml",
                "packSize": 500.0,
                "packCost": 6.00,
                "minStockQty": 1000.0,
                "category": "food",
                "wastePct": 1.0,
                "allergens": ["SOY", "GLUTEN"],
                "otherAllergens": [],
                "shelfLife": {"value": 540, "unit": "days"}
            },
            {
                "name": "Fresh Basil",
                "unit": "g",
                "packSize": 100.0,
                "packCost": 3.00,
                "minStockQty": 200.0,
                "category": "food",
                "wastePct": 25.0,
                "allergens": [],
                "otherAllergens": [],
                "shelfLife": {"value": 5, "unit": "days"}
            },
            {
                "name": "Sesame Seeds",
                "unit": "kg",
                "packSize": 1.0,
                "packCost": 8.00,
                "minStockQty": 1.0,
                "category": "food",
                "wastePct": 3.0,
                "allergens": ["SESAME"],
                "otherAllergens": [],
                "shelfLife": {"value": 180, "unit": "days"}
            },
            {
                "name": "Celery Sticks",
                "unit": "kg",
                "packSize": 2.0,
                "packCost": 4.00,
                "minStockQty": 2.0,
                "category": "food",
                "wastePct": 30.0,
                "allergens": ["CELERY"],
                "otherAllergens": [],
                "shelfLife": {"value": 7, "unit": "days"}
            }
        ]
        
        created_ingredients = {}
        
        for ing_data in ingredients:
            try:
                async with session.post(
                    f"{BACKEND_URL}/ingredients",
                    json=ing_data,
                    headers=auth_headers
                ) as response:
                    if response.status == 200:
                        ingredient = await response.json()
                        created_ingredients[ingredient["name"]] = ingredient
                        allergen_str = f"{ingredient['allergens']}" if ingredient['allergens'] else "None"
                        other_str = f" + Other: {ingredient['otherAllergens']}" if ingredient['otherAllergens'] else ""
                        print(f"✅ Created ingredient: {ingredient['name']}")
                        print(f"   Allergens: {allergen_str}{other_str}")
                    else:
                        error_text = await response.text()
                        print(f"❌ Failed to create {ing_data['name']}: {response.status} - {error_text}")
            except Exception as e:
                print(f"❌ Error creating {ing_data['name']}: {str(e)}")
        
        # Create preparation (Pasta Dough) using multiple ingredients
        if "All-Purpose Flour" in created_ingredients and "Eggs (Free Range)" in created_ingredients:
            prep_data = {
                "name": "Fresh Pasta Dough",
                "items": [
                    {
                        "ingredientId": created_ingredients["All-Purpose Flour"]["id"],
                        "qty": 1.0,
                        "unit": "kg"
                    },
                    {
                        "ingredientId": created_ingredients["Eggs (Free Range)"]["id"],
                        "qty": 6.0,
                        "unit": "pcs"
                    }
                ],
                "yield_": {"value": 10, "unit": "portions"},
                "shelfLife": {"value": 2, "unit": "days"},
                "instructions": "Mix flour and eggs to form dough. Knead for 10 minutes. Rest for 30 minutes.",
                "notes": "Should combine GLUTEN and EGGS allergens"
            }
            
            try:
                async with session.post(
                    f"{BACKEND_URL}/preparations",
                    json=prep_data,
                    headers=auth_headers
                ) as response:
                    if response.status == 200:
                        prep = await response.json()
                        created_ingredients["Fresh Pasta Dough"] = prep
                        print(f"\n✅ Created preparation: {prep['name']}")
                        print(f"   Cost: €{prep['cost']/100:.2f}")
                        print(f"   Allergens (propagated): {prep['allergens']}")
                    else:
                        error_text = await response.text()
                        print(f"❌ Failed to create preparation: {response.status} - {error_text}")
            except Exception as e:
                print(f"❌ Error creating preparation: {str(e)}")
        
        # Create recipe (Truffle Pasta) using preparation + ingredients
        if "Fresh Pasta Dough" in created_ingredients and "White Truffle Oil" in created_ingredients:
            recipe_data = {
                "name": "Truffle Pasta with Nuts",
                "category": "Pasta",
                "portions": 1,
                "price": 2500,  # €25.00
                "targetFoodCostPct": 30,
                "items": [
                    {
                        "type": "preparation",
                        "itemId": created_ingredients["Fresh Pasta Dough"]["id"],
                        "qtyPerPortion": 1.0
                    },
                    {
                        "type": "ingredient",
                        "itemId": created_ingredients["White Truffle Oil"]["id"],
                        "qtyPerPortion": 10.0
                    },
                    {
                        "type": "ingredient",
                        "itemId": created_ingredients["Mixed Nuts (Almonds, Cashews)"]["id"],
                        "qtyPerPortion": 0.03
                    },
                    {
                        "type": "ingredient",
                        "itemId": created_ingredients["Fresh Basil"]["id"],
                        "qtyPerPortion": 5.0
                    }
                ],
                "shelfLife": {"value": 1, "unit": "days"},
                "instructions": "Cook pasta. Toss with truffle oil and nuts. Garnish with basil."
            }
            
            try:
                async with session.post(
                    f"{BACKEND_URL}/recipes",
                    json=recipe_data,
                    headers=auth_headers
                ) as response:
                    if response.status == 200:
                        recipe = await response.json()
                        print(f"\n✅ Created recipe: {recipe['name']}")
                        print(f"   Price: €{recipe['price']/100:.2f}")
                        print(f"   Cost: €{recipe['cost']/100:.2f}")
                        print(f"   Allergens (aggregated): {recipe['allergens']}")
                        print(f"   Other Allergens: {recipe['otherAllergens']}")
                    else:
                        error_text = await response.text()
                        print(f"❌ Failed to create recipe: {response.status} - {error_text}")
            except Exception as e:
                print(f"❌ Error creating recipe: {str(e)}")
        
        print("\n" + "=" * 80)
        print("UAT DATA SEEDING COMPLETE")
        print(f"✅ Created {len(created_ingredients)} ingredients/preparations")
        print("=" * 80)
        print("\nYou can now test:")
        print("1. Ingredients page - Search, filter by allergen, view badges")
        print("2. Preparations page - Verify allergen propagation from ingredients")
        print("3. Recipes page - Search, filter, view allergen aggregation")
        print("4. Language switch (EN ↔ IT) - Verify all allergen labels translate")

if __name__ == "__main__":
    asyncio.run(seed_allergen_uat_data())
