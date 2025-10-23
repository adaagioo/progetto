#!/usr/bin/env python3
"""
Debug preparation cost calculation
"""

import asyncio
import aiohttp
import json

BASE_URL = "https://resto-doc-scan.preview.emergentagent.com/api"

async def debug_preparation_cost():
    async with aiohttp.ClientSession() as session:
        # Login first
        login_data = {"email": "admin@test.com", "password": "admin123"}
        async with session.post(f"{BASE_URL}/auth/login", json=login_data) as response:
            if response.status == 200:
                data = await response.json()
                token = data["access_token"]
                headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
                
                # Get cocoa ingredient
                async with session.get(f"{BASE_URL}/ingredients", headers=headers) as ing_response:
                    if ing_response.status == 200:
                        ingredients = await ing_response.json()
                        cocoa = None
                        for ing in ingredients:
                            if "Cocoa" in ing["name"]:
                                cocoa = ing
                                break
                        
                        if cocoa:
                            print("=== COCOA INGREDIENT ===")
                            print(f"ID: {cocoa['id']}")
                            print(f"Name: {cocoa['name']}")
                            print(f"Unit: {cocoa['unit']}")
                            print(f"Unit Cost: {cocoa['unitCost']} cents per {cocoa['unit']}")
                            print(f"Effective Unit Cost: {cocoa['effectiveUnitCost']} cents per {cocoa['unit']}")
                            print()
                            
                            # Test different quantities
                            test_cases = [
                                {"qty": 2, "unit": "g", "expected_cost": 2},  # 2g should cost 2 cents
                                {"qty": 1000, "unit": "g", "expected_cost": 1000},  # 1000g = 1kg should cost 1000 cents
                                {"qty": 1, "unit": "kg", "expected_cost": 1000},  # 1kg should cost 1000 cents
                            ]
                            
                            for case in test_cases:
                                prep_data = {
                                    "name": f"Test {case['qty']}{case['unit']} Cocoa",
                                    "items": [
                                        {
                                            "ingredientId": cocoa["id"],
                                            "qty": case["qty"],
                                            "unit": case["unit"]
                                        }
                                    ]
                                }
                                
                                print(f"=== TESTING {case['qty']}{case['unit']} ===")
                                print(f"Request: {json.dumps(prep_data, indent=2)}")
                                
                                async with session.post(f"{BASE_URL}/preparations", json=prep_data, headers=headers) as prep_response:
                                    if prep_response.status == 200:
                                        preparation = await prep_response.json()
                                        actual_cost = preparation["cost"]
                                        expected_cost = case["expected_cost"]
                                        
                                        print(f"Response cost: {actual_cost} cents")
                                        print(f"Expected cost: {expected_cost} cents")
                                        print(f"Match: {abs(actual_cost - expected_cost) < 0.01}")
                                        
                                        # Clean up
                                        await session.delete(f"{BASE_URL}/preparations/{preparation['id']}", headers=headers)
                                    else:
                                        error_text = await prep_response.text()
                                        print(f"Error: {prep_response.status} - {error_text}")
                                
                                print()

asyncio.run(debug_preparation_cost())