#!/usr/bin/env python3
"""
Check actual ingredient data from the backend
"""

import asyncio
import aiohttp

BASE_URL = "https://bulk-delete-rbac.preview.emergentagent.com/api"

async def check_ingredients():
    async with aiohttp.ClientSession() as session:
        # Login first
        login_data = {"email": "admin@test.com", "password": "admin123"}
        async with session.post(f"{BASE_URL}/auth/login", json=login_data) as response:
            if response.status == 200:
                data = await response.json()
                token = data["access_token"]
                headers = {"Authorization": f"Bearer {token}"}
                
                # Get ingredients
                async with session.get(f"{BASE_URL}/ingredients", headers=headers) as ing_response:
                    if ing_response.status == 200:
                        ingredients = await ing_response.json()
                        
                        print("=== INGREDIENT DATA ===")
                        for ing in ingredients:
                            if "Cocoa" in ing["name"] or "Vanilla" in ing["name"] or "Saffron" in ing["name"]:
                                print(f"\nIngredient: {ing['name']}")
                                print(f"  Unit: {ing['unit']}")
                                print(f"  Pack Size: {ing['packSize']}")
                                print(f"  Pack Cost: {ing['packCost']} (minor units)")
                                print(f"  Unit Cost: {ing['unitCost']} (minor units per {ing['unit']})")
                                print(f"  Effective Unit Cost: {ing['effectiveUnitCost']} (minor units per {ing['unit']})")
                                
                                # Convert to major units for clarity
                                pack_cost_major = ing['packCost'] / 100
                                unit_cost_major = ing['unitCost'] / 100
                                effective_unit_cost_major = ing['effectiveUnitCost'] / 100
                                
                                print(f"  Pack Cost (major): €{pack_cost_major:.2f}")
                                print(f"  Unit Cost (major): €{unit_cost_major:.2f} per {ing['unit']}")
                                print(f"  Effective Unit Cost (major): €{effective_unit_cost_major:.2f} per {ing['unit']}")

asyncio.run(check_ingredients())