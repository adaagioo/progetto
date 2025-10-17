#!/usr/bin/env python3
"""
Seed test ingredients for RistoBrain Preparations testing
"""

import asyncio
import os
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from datetime import datetime, timezone
import uuid

# Load environment
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ.get('DB_NAME', 'ristobrain_db')

async def seed_ingredients():
    """Seed test ingredients with waste percentages and allergens"""
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    print("="*60)
    print("Seeding Test Ingredients for Preparations")
    print("="*60)
    
    restaurant_id = "ristorante1"
    
    # Test ingredients with waste percentages and allergens
    test_ingredients = [
        {
            "id": str(uuid.uuid4()),
            "restaurantId": restaurant_id,
            "name": "Flour 00",
            "unit": "kg",
            "packSize": 1.0,
            "packCost": 250,  # 2.50 EUR in cents
            "unitCost": 250,
            "wastePct": 5.0,
            "effectiveUnitCost": 262,  # 2.50 * 1.05 = 2.625 EUR
            "allergens": ["gluten"],
            "category": "food",
            "minStockQty": 5,
            "shelfLife": {"value": 6, "unit": "months"},
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "updatedAt": None
        },
        {
            "id": str(uuid.uuid4()),
            "restaurantId": restaurant_id,
            "name": "Fresh Tomatoes",
            "unit": "kg",
            "packSize": 1.0,
            "packCost": 320,  # 3.20 EUR in cents
            "unitCost": 320,
            "wastePct": 15.0,
            "effectiveUnitCost": 368,  # 3.20 * 1.15 = 3.68 EUR
            "allergens": [],
            "category": "food",
            "minStockQty": 10,
            "shelfLife": {"value": 5, "unit": "days"},
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "updatedAt": None
        },
        {
            "id": str(uuid.uuid4()),
            "restaurantId": restaurant_id,
            "name": "Mozzarella di Bufala",
            "unit": "kg",
            "packSize": 1.0,
            "packCost": 1200,  # 12.00 EUR in cents
            "unitCost": 1200,
            "wastePct": 8.0,
            "effectiveUnitCost": 1296,  # 12.00 * 1.08 = 12.96 EUR
            "allergens": ["dairy"],
            "category": "food",
            "minStockQty": 5,
            "shelfLife": {"value": 7, "unit": "days"},
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "updatedAt": None
        },
        {
            "id": str(uuid.uuid4()),
            "restaurantId": restaurant_id,
            "name": "Extra Virgin Olive Oil",
            "unit": "l",
            "packSize": 1.0,
            "packCost": 850,  # 8.50 EUR in cents
            "unitCost": 850,
            "wastePct": 2.0,
            "effectiveUnitCost": 867,  # 8.50 * 1.02 = 8.67 EUR
            "allergens": [],
            "category": "food",
            "minStockQty": 3,
            "shelfLife": {"value": 12, "unit": "months"},
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "updatedAt": None
        },
        {
            "id": str(uuid.uuid4()),
            "restaurantId": restaurant_id,
            "name": "Fresh Basil",
            "unit": "kg",
            "packSize": 0.1,
            "packCost": 150,  # 1.50 EUR in cents
            "unitCost": 1500,  # 15.00 EUR per kg
            "wastePct": 20.0,
            "effectiveUnitCost": 1800,  # 15.00 * 1.20 = 18.00 EUR
            "allergens": [],
            "category": "food",
            "minStockQty": 0.5,
            "shelfLife": {"value": 3, "unit": "days"},
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "updatedAt": None
        },
        {
            "id": str(uuid.uuid4()),
            "restaurantId": restaurant_id,
            "name": "Sea Salt",
            "unit": "kg",
            "packSize": 1.0,
            "packCost": 200,  # 2.00 EUR in cents
            "unitCost": 200,
            "wastePct": 0.0,
            "effectiveUnitCost": 200,
            "allergens": [],
            "category": "food",
            "minStockQty": 2,
            "shelfLife": {"value": 24, "unit": "months"},
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "updatedAt": None
        }
    ]
    
    # Check and insert ingredients
    for ing in test_ingredients:
        existing = await db.ingredients.find_one({"name": ing["name"], "restaurantId": restaurant_id})
        if existing:
            print(f"✓ Ingredient '{ing['name']}' already exists")
        else:
            await db.ingredients.insert_one(ing)
            print(f"✓ Created ingredient: {ing['name']} (waste: {ing['wastePct']}%, allergens: {ing['allergens']})")
    
    client.close()
    
    print("\n" + "="*60)
    print("Test Ingredients Seeded Successfully!")
    print("="*60)
    print(f"\nCreated {len(test_ingredients)} ingredients for restaurant: {restaurant_id}")
    print("You can now create preparations using these ingredients.")
    print("="*60)

if __name__ == '__main__':
    asyncio.run(seed_ingredients())
