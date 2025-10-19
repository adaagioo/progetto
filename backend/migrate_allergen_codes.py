#!/usr/bin/env python3
"""
Migration script to uppercase allergen codes in existing ingredients
Handles legacy "allergen" field migration to "allergens" array
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from datetime import datetime, timezone

# Allergen code mapping
ALLERGEN_CODES = [
    "GLUTEN", "CRUSTACEANS", "MOLLUSCS", "EGGS", "FISH",
    "TREE_NUTS", "SOY", "DAIRY", "SESAME", "CELERY", "MUSTARD", "SULPHITES"
]

async def migrate_allergens():
    """Migrate all allergen data to uppercase codes"""
    mongo_url = os.getenv('MONGO_URL', 'mongodb://localhost:27017/food_analytics')
    client = AsyncIOMotorClient(mongo_url)
    db = client.food_analytics
    
    print("=" * 80)
    print("ALLERGEN CODE MIGRATION SCRIPT")
    print("=" * 80)
    
    # Count ingredients needing migration
    ingredients_cursor = db.ingredients.find({})
    total_ingredients = 0
    migrated_count = 0
    already_uppercase = 0
    
    async for ingredient in ingredients_cursor:
        total_ingredients += 1
        needs_update = False
        updates = {}
        
        # Migrate legacy "allergen" field to "allergens" array
        if "allergen" in ingredient and ingredient["allergen"]:
            legacy_allergen = ingredient["allergen"].strip().upper().replace(" ", "_")
            if legacy_allergen in ALLERGEN_CODES:
                # Add to allergens array
                current_allergens = set(ingredient.get("allergens", []))
                current_allergens.add(legacy_allergen)
                updates["allergens"] = sorted(list(current_allergens))
            else:
                # Add to otherAllergens
                current_other = set(ingredient.get("otherAllergens", []))
                current_other.add(ingredient["allergen"])
                updates["otherAllergens"] = sorted(list(current_other))
            
            # Remove legacy field
            updates["allergen"] = None
            needs_update = True
            print(f"✓ Migrating legacy allergen '{ingredient['allergen']}' for: {ingredient['name']}")
        
        # Uppercase existing allergen codes
        if "allergens" in ingredient and ingredient["allergens"]:
            original_allergens = ingredient["allergens"]
            uppercased_allergens = [a.upper() for a in original_allergens]
            
            if original_allergens != uppercased_allergens:
                updates["allergens"] = sorted(uppercased_allergens)
                needs_update = True
                print(f"✓ Uppercasing allergens for: {ingredient['name']}")
                print(f"  From: {original_allergens}")
                print(f"  To: {uppercased_allergens}")
            else:
                already_uppercase += 1
        
        # Apply updates
        if needs_update:
            await db.ingredients.update_one(
                {"_id": ingredient["_id"]},
                {"$set": updates}
            )
            migrated_count += 1
    
    print("\n" + "=" * 80)
    print(f"MIGRATION COMPLETE")
    print(f"Total ingredients processed: {total_ingredients}")
    print(f"Ingredients migrated: {migrated_count}")
    print(f"Already uppercase: {already_uppercase}")
    print("=" * 80)
    
    # Verify migration
    print("\nVerifying migration...")
    lowercase_found = 0
    cursor = db.ingredients.find({"allergens": {"$exists": True, "$ne": []}})
    
    async for ing in cursor:
        for allergen in ing.get("allergens", []):
            if allergen != allergen.upper():
                lowercase_found += 1
                print(f"⚠️  Found lowercase allergen '{allergen}' in: {ing['name']}")
    
    if lowercase_found == 0:
        print("✅ All allergen codes are now uppercase!")
    else:
        print(f"❌ {lowercase_found} lowercase allergens still found!")
    
    # Check for legacy "allergen" field
    legacy_count = await db.ingredients.count_documents({"allergen": {"$ne": None, "$exists": True}})
    if legacy_count == 0:
        print("✅ No legacy 'allergen' field found!")
    else:
        print(f"⚠️  {legacy_count} ingredients still have legacy 'allergen' field")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(migrate_allergens())
