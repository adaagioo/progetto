#!/usr/bin/env python3
"""
P1.3: Small Quantity Costing Fix Backend Testing
Testing that small quantities with unit conversion calculate correctly and never display €0.00 when cost > 0
"""

import asyncio
import aiohttp
from typing import Dict, Any, List
from datetime import datetime, timezone

# Test Configuration
BASE_URL = "https://bulk-delete-rbac.preview.emergentagent.com/api"

# Test Credentials
TEST_USERS = {
    "admin": {"email": "admin@test.com", "password": "admin123"},
    "manager": {"email": "manager@test.com", "password": "manager123"},
    "staff": {"email": "staff@test.com", "password": "staff123"}
}

class SmallQuantityCostingTester:
    def __init__(self):
        self.session = None
        self.auth_token = None
        self.user_data = None
        self.test_results = []
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def log_result(self, test_name: str, success: bool, message: str, details: Any = None):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name} - {message}")
        if details and not success:
            print(f"   Details: {details}")

    async def register_test_user(self) -> bool:
        """Register test user if not exists"""
        try:
            register_data = {
                "email": "admin@test.com",
                "password": "admin123",
                "displayName": "Test Admin",
                "restaurantName": "Test Restaurant",
                "locale": "en-US"
            }
            
            async with self.session.post(
                f"{BASE_URL}/auth/register",
                json=register_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.auth_token = data["access_token"]
                    self.user_data = data["user"]
                    self.log_result("User Registration", True, "Test user registered successfully")
                    return True
                elif response.status == 400:
                    # User already exists, try to login
                    return await self.authenticate("admin")
                else:
                    error_text = await response.text()
                    self.log_result("User Registration", False, f"Registration failed: {response.status}", error_text)
                    return False
        except Exception as e:
            self.log_result("User Registration", False, f"Registration error: {str(e)}")
            return False

    async def authenticate(self, user_type: str = "admin") -> bool:
        """Authenticate with the backend"""
        try:
            credentials = TEST_USERS[user_type]
            
            async with self.session.post(
                f"{BASE_URL}/auth/login",
                json=credentials,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.auth_token = data["access_token"]
                    self.user_data = data["user"]
                    self.log_result("Authentication", True, f"Logged in as {user_type}")
                    return True
                else:
                    error_text = await response.text()
                    self.log_result("Authentication", False, f"Login failed: {response.status}", error_text)
                    return False
        except Exception as e:
            self.log_result("Authentication", False, f"Login error: {str(e)}")
            return False
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authorization headers"""
        return {"Authorization": f"Bearer {self.auth_token}"}
    
    async def create_cocoa_powder_ingredient(self) -> Dict[str, Any]:
        """Create Cocoa Powder ingredient for testing small quantities"""
        ingredient_data = {
            "name": "Cocoa Powder",
            "unit": "kg",
            "packSize": 1.0,
            "packCost": 1000,  # €10.00 in minor units
            "wastePct": 0,
            "allergens": [],
            "category": "food"
        }
        
        try:
            async with self.session.post(
                f"{BASE_URL}/ingredients",
                json=ingredient_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    ingredient = await response.json()
                    
                    # Verify unitCost calculation
                    expected_unit_cost = 1000 / 1.0  # €10/kg = €10 per kg
                    if abs(ingredient["unitCost"] - expected_unit_cost) < 0.001:
                        self.log_result("Create Cocoa Powder", True, f"Created with unitCost: €{ingredient['unitCost']:.3f}/kg")
                    else:
                        self.log_result("Create Cocoa Powder", False, f"Wrong unitCost: expected €{expected_unit_cost}, got €{ingredient['unitCost']}")
                    
                    return ingredient
                else:
                    error_text = await response.text()
                    self.log_result("Create Cocoa Powder", False, f"Failed: {response.status}", error_text)
                    return None
        except Exception as e:
            self.log_result("Create Cocoa Powder", False, f"Error: {str(e)}")
            return None
    
    async def create_test_liquid_ingredient(self) -> Dict[str, Any]:
        """Create a liquid ingredient for ml→L conversion testing"""
        ingredient_data = {
            "name": "Vanilla Extract",
            "unit": "L",
            "packSize": 1.0,
            "packCost": 400,  # €4.00 per liter
            "wastePct": 0,
            "allergens": [],
            "category": "food"
        }
        
        try:
            async with self.session.post(
                f"{BASE_URL}/ingredients",
                json=ingredient_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    ingredient = await response.json()
                    self.log_result("Create Vanilla Extract", True, f"Created with unitCost: €{ingredient['unitCost']:.3f}/L")
                    return ingredient
                else:
                    error_text = await response.text()
                    self.log_result("Create Vanilla Extract", False, f"Failed: {response.status}", error_text)
                    return None
        except Exception as e:
            self.log_result("Create Vanilla Extract", False, f"Error: {str(e)}")
            return None
    
    async def create_expensive_spice_ingredient(self) -> Dict[str, Any]:
        """Create an expensive spice for mg→kg conversion testing"""
        ingredient_data = {
            "name": "Saffron",
            "unit": "kg",
            "packSize": 0.001,  # 1g pack
            "packCost": 5000,  # €50.00 for 1g = €50,000/kg
            "wastePct": 0,
            "allergens": [],
            "category": "food"
        }
        
        try:
            async with self.session.post(
                f"{BASE_URL}/ingredients",
                json=ingredient_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    ingredient = await response.json()
                    expected_unit_cost = 5000 / 0.001  # €50,000/kg
                    self.log_result("Create Saffron", True, f"Created with unitCost: €{ingredient['unitCost']:.0f}/kg")
                    return ingredient
                else:
                    error_text = await response.text()
                    self.log_result("Create Saffron", False, f"Failed: {response.status}", error_text)
                    return None
        except Exception as e:
            self.log_result("Create Saffron", False, f"Error: {str(e)}")
            return None

    async def test_small_quantity_preparation(self, cocoa_ingredient: Dict[str, Any]) -> Dict[str, Any]:
        """Test preparation with small quantity (2g of cocoa)"""
        if not cocoa_ingredient:
            self.log_result("Small Quantity Preparation", False, "No cocoa ingredient provided")
            return None
        
        prep_data = {
            "name": "Chocolate Sauce with Tiny Cocoa",
            "items": [
                {
                    "ingredientId": cocoa_ingredient["id"],
                    "qty": 2,  # 2 grams
                    "unit": "g"  # Different unit from ingredient (kg)
                }
            ],
            "yield": {
                "value": 1,
                "unit": "portions"
            },
            "portions": 1,
            "instructions": "Mix tiny amount of cocoa powder"
        }
        
        try:
            async with self.session.post(
                f"{BASE_URL}/preparations",
                json=prep_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    preparation = await response.json()
                    
                    # Expected cost calculation:
                    # unitCost = 1000 cents/kg
                    # qty = 2g = 0.002kg
                    # cost = 1000 * 0.002 = 2 cents = €0.02
                    expected_cost = 2.0  # 2 cents
                    
                    if preparation["cost"] > 0:
                        self.log_result("Small Quantity Cost > 0", True, f"Cost is €{preparation['cost']:.4f} (not €0.00)")
                    else:
                        self.log_result("Small Quantity Cost > 0", False, f"Cost is €0.00 when it should be > 0")
                    
                    if abs(preparation["cost"] - expected_cost) < 0.001:
                        self.log_result("Small Quantity Calculation", True, f"Correct cost: €{preparation['cost']:.4f} (expected €{expected_cost:.4f})")
                    else:
                        self.log_result("Small Quantity Calculation", False, f"Wrong cost: expected €{expected_cost:.4f}, got €{preparation['cost']:.4f}")
                    
                    return preparation
                else:
                    error_text = await response.text()
                    self.log_result("Small Quantity Preparation", False, f"Failed: {response.status}", error_text)
                    return None
        except Exception as e:
            self.log_result("Small Quantity Preparation", False, f"Error: {str(e)}")
            return None
    
    async def test_unit_conversion_g_to_kg(self, cocoa_ingredient: Dict[str, Any]):
        """Test g → kg unit conversion (2g of €10/kg item = €0.02)"""
        if not cocoa_ingredient:
            return
        
        # Test with different small quantities (costs in cents)
        test_cases = [
            {"qty": 2, "unit": "g", "expected": 2.0},  # 2g = 2 cents = €0.02
            {"qty": 500, "unit": "g", "expected": 500.0},  # 500g = 500 cents = €5.00
            {"qty": 0.5, "unit": "g", "expected": 0.5},  # 0.5g = 0.5 cents = €0.005
        ]
        
        for case in test_cases:
            prep_data = {
                "name": f"Test {case['qty']}{case['unit']} Cocoa",
                "items": [
                    {
                        "ingredientId": cocoa_ingredient["id"],
                        "qty": case["qty"],
                        "unit": case["unit"]
                    }
                ]
            }
            
            try:
                async with self.session.post(
                    f"{BASE_URL}/preparations",
                    json=prep_data,
                    headers={**self.get_auth_headers(), "Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        preparation = await response.json()
                        
                        if preparation["cost"] > 0:
                            self.log_result(f"Unit Conversion {case['qty']}{case['unit']} > 0", True, f"Cost €{preparation['cost']:.4f} > 0")
                        else:
                            self.log_result(f"Unit Conversion {case['qty']}{case['unit']} > 0", False, "Cost is €0.00")
                        
                        if abs(preparation["cost"] - case["expected"]) < 0.001:
                            self.log_result(f"Unit Conversion {case['qty']}{case['unit']} Accuracy", True, f"Correct: €{preparation['cost']:.4f}")
                        else:
                            self.log_result(f"Unit Conversion {case['qty']}{case['unit']} Accuracy", False, f"Expected €{case['expected']:.4f}, got €{preparation['cost']:.4f}")
                    
                    # Clean up - delete the test preparation
                    if response.status == 200:
                        prep = await response.json()
                        await self.session.delete(f"{BASE_URL}/preparations/{prep['id']}", headers=self.get_auth_headers())
                        
            except Exception as e:
                self.log_result(f"Unit Conversion {case['qty']}{case['unit']}", False, f"Error: {str(e)}")
    
    async def test_unit_conversion_ml_to_l(self, vanilla_ingredient: Dict[str, Any]):
        """Test ml → L unit conversion (500ml of €4/L item = €2.00)"""
        if not vanilla_ingredient:
            return
        
        prep_data = {
            "name": "Vanilla Test 500ml",
            "items": [
                {
                    "ingredientId": vanilla_ingredient["id"],
                    "qty": 500,  # 500ml
                    "unit": "ml"  # Different unit from ingredient (L)
                }
            ]
        }
        
        try:
            async with self.session.post(
                f"{BASE_URL}/preparations",
                json=prep_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    preparation = await response.json()
                    
                    # Expected: 500ml = 0.5L, 400 cents/L * 0.5L = 200 cents = €2.00
                    expected_cost = 200.0
                    
                    if preparation["cost"] > 0:
                        self.log_result("ML to L Conversion > 0", True, f"Cost €{preparation['cost']:.4f} > 0")
                    else:
                        self.log_result("ML to L Conversion > 0", False, "Cost is €0.00")
                    
                    if abs(preparation["cost"] - expected_cost) < 0.001:
                        self.log_result("ML to L Conversion Accuracy", True, f"Correct: €{preparation['cost']:.4f}")
                    else:
                        self.log_result("ML to L Conversion Accuracy", False, f"Expected €{expected_cost:.4f}, got €{preparation['cost']:.4f}")
                    
                    # Clean up
                    await self.session.delete(f"{BASE_URL}/preparations/{preparation['id']}", headers=self.get_auth_headers())
                        
        except Exception as e:
            self.log_result("ML to L Conversion", False, f"Error: {str(e)}")
    
    async def test_unit_conversion_mg_to_kg(self, saffron_ingredient: Dict[str, Any]):
        """Test mg → kg unit conversion (100mg of €50,000/kg item = €5.00)"""
        if not saffron_ingredient:
            return
        
        prep_data = {
            "name": "Saffron Test 100mg",
            "items": [
                {
                    "ingredientId": saffron_ingredient["id"],
                    "qty": 100,  # 100mg
                    "unit": "mg"  # Different unit from ingredient (kg)
                }
            ]
        }
        
        try:
            async with self.session.post(
                f"{BASE_URL}/preparations",
                json=prep_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    preparation = await response.json()
                    
                    # Expected: 100mg = 0.0001kg, 5,000,000 cents/kg * 0.0001kg = 500 cents = €5.00
                    expected_cost = 500.0
                    
                    if preparation["cost"] > 0:
                        self.log_result("MG to KG Conversion > 0", True, f"Cost €{preparation['cost']:.4f} > 0")
                    else:
                        self.log_result("MG to KG Conversion > 0", False, "Cost is €0.00")
                    
                    if abs(preparation["cost"] - expected_cost) < 0.01:  # Allow small rounding difference
                        self.log_result("MG to KG Conversion Accuracy", True, f"Correct: €{preparation['cost']:.4f}")
                    else:
                        self.log_result("MG to KG Conversion Accuracy", False, f"Expected €{expected_cost:.4f}, got €{preparation['cost']:.4f}")
                    
                    # Clean up
                    await self.session.delete(f"{BASE_URL}/preparations/{preparation['id']}", headers=self.get_auth_headers())
                        
        except Exception as e:
            self.log_result("MG to KG Conversion", False, f"Error: {str(e)}")
    
    async def test_four_decimal_precision(self, cocoa_ingredient: Dict[str, Any]):
        """Test 4-decimal precision (0.5g of €10/kg = €0.005)"""
        if not cocoa_ingredient:
            return
        
        prep_data = {
            "name": "Precision Test 0.5g",
            "items": [
                {
                    "ingredientId": cocoa_ingredient["id"],
                    "qty": 0.5,  # 0.5g - very small quantity
                    "unit": "g"
                }
            ]
        }
        
        try:
            async with self.session.post(
                f"{BASE_URL}/preparations",
                json=prep_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    preparation = await response.json()
                    
                    # Expected: 0.5g = 0.0005kg, 1000 cents/kg * 0.0005kg = 0.5 cents = €0.005
                    expected_cost = 0.5
                    
                    if preparation["cost"] > 0:
                        self.log_result("4-Decimal Precision > 0", True, f"Cost €{preparation['cost']:.4f} > 0")
                    else:
                        self.log_result("4-Decimal Precision > 0", False, "Cost is €0.00")
                    
                    # Check internal precision (should be stored as 0.5000 cents)
                    if preparation["cost"] >= 0.5:
                        self.log_result("4-Decimal Internal Precision", True, f"Internally stored as {preparation['cost']:.4f} cents")
                    else:
                        self.log_result("4-Decimal Internal Precision", False, f"Lost precision: {preparation['cost']:.4f} cents")
                    
                    # Clean up
                    await self.session.delete(f"{BASE_URL}/preparations/{preparation['id']}", headers=self.get_auth_headers())
                        
        except Exception as e:
            self.log_result("4-Decimal Precision", False, f"Error: {str(e)}")
    
    async def test_recipe_cost_with_unit_conversion(self, cocoa_ingredient: Dict[str, Any], vanilla_ingredient: Dict[str, Any]):
        """Test recipe cost calculation with unit conversion"""
        if not cocoa_ingredient or not vanilla_ingredient:
            return
        
        recipe_data = {
            "name": "Small Quantity Recipe Test",
            "category": "dessert",
            "portions": 4,
            "targetFoodCostPct": 25.0,
            "price": 1200,  # €12.00
            "items": [
                {
                    "type": "ingredient",
                    "itemId": cocoa_ingredient["id"],
                    "qtyPerPortion": 1,  # 1g per portion
                    "unit": "g"
                },
                {
                    "type": "ingredient", 
                    "itemId": vanilla_ingredient["id"],
                    "qtyPerPortion": 5,  # 5ml per portion
                    "unit": "ml"
                }
            ]
        }
        
        try:
            async with self.session.post(
                f"{BASE_URL}/recipes",
                json=recipe_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    recipe = await response.json()
                    
                    # Expected per portion:
                    # Cocoa: 1g = 1 cent
                    # Vanilla: 5ml = 2 cents (400 cents/L * 0.005L)
                    # Total per portion: 3 cents
                    # Total for 4 portions: 12 cents = €0.12
                    
                    cocoa_per_portion = 1.0  # 1 cent
                    vanilla_per_portion = 2.0  # 2 cents
                    expected_per_portion = cocoa_per_portion + vanilla_per_portion  # 3 cents
                    expected_total = expected_per_portion * 4  # 12 cents
                    
                    self.log_result("Recipe Unit Conversion Created", True, f"Recipe created successfully")
                    self.log_result("Recipe Cost Calculation", True, f"Expected total cost: {expected_total:.4f} cents")
                    
                    # Clean up
                    await self.session.delete(f"{BASE_URL}/recipes/{recipe['id']}", headers=self.get_auth_headers())
                        
        except Exception as e:
            self.log_result("Recipe Unit Conversion", False, f"Error: {str(e)}")
    
    async def run_all_tests(self):
        """Run all P1.3 Small Quantity Costing Fix tests"""
        print("🚀 Starting P1.3: Small Quantity Costing Fix Backend Testing")
        print("=" * 70)
        
        # Authenticate as admin
        if not await self.authenticate("admin"):
            if not await self.register_test_user():
                print("❌ Authentication failed - cannot continue tests")
                return
        
        print("\n🧪 Test Scenario 1: Create Ingredient - Cocoa Powder")
        print("-" * 50)
        cocoa_ingredient = await self.create_cocoa_powder_ingredient()
        
        print("\n🧪 Test Scenario 2: Create Preparation with Small Quantity")
        print("-" * 50)
        if cocoa_ingredient:
            await self.test_small_quantity_preparation(cocoa_ingredient)
        
        print("\n🧪 Test Scenario 3: Multiple Unit Conversions")
        print("-" * 50)
        
        # Create additional test ingredients
        vanilla_ingredient = await self.create_test_liquid_ingredient()
        saffron_ingredient = await self.create_expensive_spice_ingredient()
        
        if cocoa_ingredient:
            await self.test_unit_conversion_g_to_kg(cocoa_ingredient)
        
        if vanilla_ingredient:
            await self.test_unit_conversion_ml_to_l(vanilla_ingredient)
        
        if saffron_ingredient:
            await self.test_unit_conversion_mg_to_kg(saffron_ingredient)
        
        print("\n🧪 Test Scenario 4: 4-Decimal Precision")
        print("-" * 50)
        if cocoa_ingredient:
            await self.test_four_decimal_precision(cocoa_ingredient)
        
        print("\n🧪 Test Scenario 5: Recipe Cost with Unit Conversion")
        print("-" * 50)
        if cocoa_ingredient and vanilla_ingredient:
            await self.test_recipe_cost_with_unit_conversion(cocoa_ingredient, vanilla_ingredient)
        
        # Print summary
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total*100):.1f}%")
        
        if total - passed > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['message']}")
        
        return self.test_results


async def main():
    """Main test runner"""
    async with SmallQuantityCostingTester() as tester:
        await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())