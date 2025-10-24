#!/usr/bin/env python3
"""
P2 Feature: Recipe Dependencies & Bulk Delete Backend Testing
Testing recipe dependencies endpoint, delete with dependency blocking, and RBAC enforcement
"""

import requests
import json
import asyncio
import aiohttp
from typing import Dict, Any, List
from datetime import datetime, timezone

# Test Configuration
BASE_URL = "https://menuflow-8.preview.emergentagent.com/api"

# Test Credentials
TEST_USERS = {
    "admin": {"email": "admin@test.com", "password": "admin123"},
    "manager": {"email": "manager@test.com", "password": "manager123"},
    "staff": {"email": "staff@test.com", "password": "staff123"}
}

class RecipeDependenciesTester:
    def __init__(self):
        self.session = None
        self.auth_token = None
        self.user_data = None
        self.test_results = []
        self.test_recipes = []
        self.test_ingredients = []
        
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
    
    async def create_test_ingredients(self) -> List[Dict[str, Any]]:
        """Create test ingredients for recipes"""
        ingredients_data = [
            {
                "name": "Test Flour",
                "unit": "kg",
                "packSize": 1.0,
                "packCost": 250,  # €2.50
                "wastePct": 5.0,
                "allergens": ["GLUTEN"],
                "category": "food"
            },
            {
                "name": "Test Tomatoes",
                "unit": "kg", 
                "packSize": 1.0,
                "packCost": 320,  # €3.20
                "wastePct": 15.0,
                "allergens": [],
                "category": "food"
            },
            {
                "name": "Test Mozzarella",
                "unit": "kg",
                "packSize": 1.0,
                "packCost": 1200,  # €12.00
                "wastePct": 8.0,
                "allergens": ["DAIRY"],
                "category": "food"
            }
        ]
        
        created_ingredients = []
        
        for ingredient_data in ingredients_data:
            try:
                async with self.session.post(
                    f"{BASE_URL}/ingredients",
                    json=ingredient_data,
                    headers={**self.get_auth_headers(), "Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        ingredient = await response.json()
                        created_ingredients.append(ingredient)
                        self.log_result("Create Test Ingredient", True, f"Created {ingredient['name']}")
                    else:
                        error_text = await response.text()
                        self.log_result("Create Test Ingredient", False, f"Failed to create {ingredient_data['name']}: {response.status}", error_text)
            except Exception as e:
                self.log_result("Create Test Ingredient", False, f"Error creating {ingredient_data['name']}: {str(e)}")
        
        self.test_ingredients = created_ingredients
        return created_ingredients
    
    async def create_test_recipes(self, ingredients: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create 3 test recipes for bulk delete testing"""
        if len(ingredients) < 3:
            self.log_result("Create Test Recipes", False, "Not enough ingredients available")
            return []
        
        recipes_data = [
            {
                "name": "Test Recipe 1 - Simple Bread",
                "category": "bread",
                "portions": 4,
                "targetFoodCostPct": 25.0,
                "price": 800,  # €8.00
                "items": [
                    {
                        "type": "ingredient",
                        "itemId": ingredients[0]["id"],  # Flour
                        "qtyPerPortion": 0.25,
                        "unit": "kg"
                    }
                ]
            },
            {
                "name": "Test Recipe 2 - Tomato Salad",
                "category": "salad",
                "portions": 2,
                "targetFoodCostPct": 30.0,
                "price": 600,  # €6.00
                "items": [
                    {
                        "type": "ingredient",
                        "itemId": ingredients[1]["id"],  # Tomatoes
                        "qtyPerPortion": 0.3,
                        "unit": "kg"
                    }
                ]
            },
            {
                "name": "Test Recipe 3 - Cheese Plate",
                "category": "appetizer",
                "portions": 1,
                "targetFoodCostPct": 35.0,
                "price": 1200,  # €12.00
                "items": [
                    {
                        "type": "ingredient",
                        "itemId": ingredients[2]["id"],  # Mozzarella
                        "qtyPerPortion": 0.2,
                        "unit": "kg"
                    }
                ]
            }
        ]
        
        created_recipes = []
        
        for recipe_data in recipes_data:
            try:
                async with self.session.post(
                    f"{BASE_URL}/recipes",
                    json=recipe_data,
                    headers={**self.get_auth_headers(), "Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        recipe = await response.json()
                        created_recipes.append(recipe)
                        self.log_result("Create Test Recipe", True, f"Created {recipe['name']}")
                    else:
                        error_text = await response.text()
                        self.log_result("Create Test Recipe", False, f"Failed to create {recipe_data['name']}: {response.status}", error_text)
            except Exception as e:
                self.log_result("Create Test Recipe", False, f"Error creating {recipe_data['name']}: {str(e)}")
        
        self.test_recipes = created_recipes
        return created_recipes
    
    async def test_recipe_dependencies_endpoint_no_sales(self, recipe: Dict[str, Any]):
        """Test dependencies endpoint for recipe with no sales"""
        if not recipe:
            self.log_result("Dependencies No Sales", False, "No recipe provided")
            return
        
        try:
            async with self.session.get(
                f"{BASE_URL}/recipes/{recipe['id']}/dependencies",
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 200:
                    deps = await response.json()
                    
                    # Verify response structure
                    required_fields = ["hasReferences", "references"]
                    if not all(field in deps for field in required_fields):
                        self.log_result("Dependencies No Sales", False, f"Missing fields in response: {deps}")
                        return
                    
                    # Should have no references
                    if not deps["hasReferences"] and deps["references"]["sales"] == 0:
                        self.log_result("Dependencies No Sales", True, "Correctly shows no dependencies")
                    else:
                        self.log_result("Dependencies No Sales", False, f"Should show no dependencies: {deps}")
                else:
                    error_text = await response.text()
                    self.log_result("Dependencies No Sales", False, f"Failed: {response.status}", error_text)
        except Exception as e:
            self.log_result("Dependencies No Sales", False, f"Error: {str(e)}")
    
    async def create_sales_record(self, recipe: Dict[str, Any]) -> Dict[str, Any]:
        """Create a sales record referencing a recipe"""
        if not recipe:
            self.log_result("Create Sales Record", False, "No recipe provided")
            return None
        
        sales_data = {
            "date": "2024-01-15",
            "lines": [
                {
                    "recipeId": recipe["id"],
                    "qty": 2  # 2 portions sold
                }
            ],
            "revenue": 1600,  # €16.00 for 2 portions
            "notes": "Test sales record for dependency testing"
        }
        
        try:
            async with self.session.post(
                f"{BASE_URL}/sales",
                json=sales_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    sales = await response.json()
                    self.log_result("Create Sales Record", True, f"Created sales record for {recipe['name']}")
                    return sales
                else:
                    error_text = await response.text()
                    self.log_result("Create Sales Record", False, f"Failed: {response.status}", error_text)
                    return None
        except Exception as e:
            self.log_result("Create Sales Record", False, f"Error: {str(e)}")
            return None
    
    async def test_recipe_dependencies_endpoint_with_sales(self, recipe: Dict[str, Any]):
        """Test dependencies endpoint for recipe with sales"""
        if not recipe:
            self.log_result("Dependencies With Sales", False, "No recipe provided")
            return
        
        try:
            async with self.session.get(
                f"{BASE_URL}/recipes/{recipe['id']}/dependencies",
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 200:
                    deps = await response.json()
                    
                    # Should have references
                    if deps["hasReferences"] and deps["references"]["sales"] > 0:
                        self.log_result("Dependencies With Sales", True, f"Correctly detected {deps['references']['sales']} sales references")
                    else:
                        self.log_result("Dependencies With Sales", False, f"Should show sales dependencies: {deps}")
                else:
                    error_text = await response.text()
                    self.log_result("Dependencies With Sales", False, f"Failed: {response.status}", error_text)
        except Exception as e:
            self.log_result("Dependencies With Sales", False, f"Error: {str(e)}")
    
    async def test_delete_recipe_without_dependencies(self, recipe: Dict[str, Any]):
        """Test deleting recipe without dependencies (should succeed)"""
        if not recipe:
            self.log_result("Delete Without Dependencies", False, "No recipe provided")
            return False
        
        try:
            async with self.session.delete(
                f"{BASE_URL}/recipes/{recipe['id']}",
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    self.log_result("Delete Without Dependencies", True, f"Successfully deleted {recipe['name']}")
                    return True
                else:
                    error_text = await response.text()
                    self.log_result("Delete Without Dependencies", False, f"Failed: {response.status}", error_text)
                    return False
        except Exception as e:
            self.log_result("Delete Without Dependencies", False, f"Error: {str(e)}")
            return False
    
    async def test_delete_recipe_with_dependencies(self, recipe: Dict[str, Any]):
        """Test deleting recipe with dependencies (should fail with 400)"""
        if not recipe:
            self.log_result("Delete With Dependencies", False, "No recipe provided")
            return
        
        try:
            async with self.session.delete(
                f"{BASE_URL}/recipes/{recipe['id']}",
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 400:
                    error_data = await response.json()
                    error_message = error_data.get("detail", "")
                    
                    # Check if error message mentions sales count
                    if "sales records" in error_message and "referenced" in error_message:
                        self.log_result("Delete With Dependencies", True, f"Correctly blocked deletion: {error_message}")
                    else:
                        self.log_result("Delete With Dependencies", False, f"Wrong error message: {error_message}")
                else:
                    error_text = await response.text()
                    self.log_result("Delete With Dependencies", False, f"Should return 400 error: {response.status}", error_text)
        except Exception as e:
            self.log_result("Delete With Dependencies", False, f"Error: {str(e)}")
    
    async def test_rbac_admin_can_delete(self, recipe: Dict[str, Any]):
        """Test that admin can delete recipes"""
        if not recipe:
            self.log_result("RBAC Admin Delete", False, "No recipe provided")
            return
        
        # Ensure we're authenticated as admin
        if not await self.authenticate("admin"):
            self.log_result("RBAC Admin Delete", False, "Could not authenticate as admin")
            return
        
        try:
            async with self.session.delete(
                f"{BASE_URL}/recipes/{recipe['id']}",
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 200:
                    self.log_result("RBAC Admin Delete", True, "Admin can delete recipes")
                elif response.status == 400:
                    # If it's a dependency error, that's expected behavior
                    error_data = await response.json()
                    if "referenced" in error_data.get("detail", ""):
                        self.log_result("RBAC Admin Delete", True, "Admin delete blocked by dependencies (correct)")
                    else:
                        self.log_result("RBAC Admin Delete", False, f"Unexpected 400 error: {error_data}")
                else:
                    error_text = await response.text()
                    self.log_result("RBAC Admin Delete", False, f"Admin delete failed: {response.status}", error_text)
        except Exception as e:
            self.log_result("RBAC Admin Delete", False, f"Error: {str(e)}")
    
    async def test_rbac_manager_can_delete(self, recipe: Dict[str, Any]):
        """Test that manager can delete recipes"""
        if not recipe:
            self.log_result("RBAC Manager Delete", False, "No recipe provided")
            return
        
        # Authenticate as manager
        if not await self.authenticate("manager"):
            self.log_result("RBAC Manager Delete", False, "Could not authenticate as manager")
            return
        
        try:
            async with self.session.delete(
                f"{BASE_URL}/recipes/{recipe['id']}",
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 200:
                    self.log_result("RBAC Manager Delete", True, "Manager can delete recipes")
                elif response.status == 400:
                    # If it's a dependency error, that's expected behavior
                    error_data = await response.json()
                    if "referenced" in error_data.get("detail", ""):
                        self.log_result("RBAC Manager Delete", True, "Manager delete blocked by dependencies (correct)")
                    else:
                        self.log_result("RBAC Manager Delete", False, f"Unexpected 400 error: {error_data}")
                else:
                    error_text = await response.text()
                    self.log_result("RBAC Manager Delete", False, f"Manager delete failed: {response.status}", error_text)
        except Exception as e:
            self.log_result("RBAC Manager Delete", False, f"Error: {str(e)}")
    
    async def test_rbac_staff_cannot_delete(self, recipe: Dict[str, Any]):
        """Test that staff cannot delete recipes"""
        if not recipe:
            self.log_result("RBAC Staff Delete", False, "No recipe provided")
            return
        
        # Authenticate as staff
        if not await self.authenticate("staff"):
            self.log_result("RBAC Staff Delete", False, "Could not authenticate as staff")
            return
        
        try:
            async with self.session.delete(
                f"{BASE_URL}/recipes/{recipe['id']}",
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 403:
                    error_data = await response.json()
                    if "Admin or Manager access required" in error_data.get("detail", ""):
                        self.log_result("RBAC Staff Delete", True, "Staff correctly denied delete access")
                    else:
                        self.log_result("RBAC Staff Delete", False, f"Wrong error message: {error_data}")
                else:
                    error_text = await response.text()
                    self.log_result("RBAC Staff Delete", False, f"Staff should be denied: {response.status}", error_text)
        except Exception as e:
            self.log_result("RBAC Staff Delete", False, f"Error: {str(e)}")
    
    async def cleanup_test_data(self):
        """Clean up test data"""
        # Re-authenticate as admin for cleanup
        await self.authenticate("admin")
        
        # Delete any remaining test recipes
        for recipe in self.test_recipes:
            try:
                async with self.session.delete(
                    f"{BASE_URL}/recipes/{recipe['id']}",
                    headers=self.get_auth_headers()
                ) as response:
                    pass  # Ignore errors during cleanup
            except:
                pass
        
        # Delete test ingredients
        for ingredient in self.test_ingredients:
            try:
                async with self.session.delete(
                    f"{BASE_URL}/ingredients/{ingredient['id']}",
                    headers=self.get_auth_headers()
                ) as response:
                    pass  # Ignore errors during cleanup
            except:
                pass
    
    async def run_all_tests(self):
        """Run all P2 Recipe Dependencies & Bulk Delete tests"""
        print("🚀 Starting P2: Recipe Dependencies & Bulk Delete Backend Testing")
        print("=" * 80)
        
        # Authenticate as admin
        if not await self.authenticate("admin"):
            print("❌ Authentication failed - cannot continue tests")
            return
        
        print("\n🧪 Test Setup: Create Test Data")
        print("-" * 50)
        
        # Create test ingredients
        ingredients = await self.create_test_ingredients()
        if len(ingredients) < 3:
            print("❌ Failed to create required test ingredients")
            return
        
        # Create test recipes
        recipes = await self.create_test_recipes(ingredients)
        if len(recipes) < 3:
            print("❌ Failed to create required test recipes")
            return
        
        print("\n🧪 Test 1: Recipe Dependencies Endpoint (No Sales)")
        print("-" * 50)
        
        # Test dependencies endpoint for recipes without sales
        for i, recipe in enumerate(recipes):
            await self.test_recipe_dependencies_endpoint_no_sales(recipe)
        
        print("\n🧪 Test 2: Create Sales Record")
        print("-" * 50)
        
        # Create a sales record for the first recipe
        sales_record = await self.create_sales_record(recipes[0])
        
        print("\n🧪 Test 3: Recipe Dependencies Endpoint (With Sales)")
        print("-" * 50)
        
        # Test dependencies endpoint for recipe with sales
        await self.test_recipe_dependencies_endpoint_with_sales(recipes[0])
        
        print("\n🧪 Test 4: Delete Recipe With Dependencies (Should Fail)")
        print("-" * 50)
        
        # Try to delete recipe with sales (should fail)
        await self.test_delete_recipe_with_dependencies(recipes[0])
        
        print("\n🧪 Test 5: Delete Recipes Without Dependencies (Should Succeed)")
        print("-" * 50)
        
        # Delete recipes without sales (should succeed)
        await self.test_delete_recipe_without_dependencies(recipes[1])
        await self.test_delete_recipe_without_dependencies(recipes[2])
        
        print("\n🧪 Test 6: RBAC Enforcement - Admin Can Delete")
        print("-" * 50)
        
        # Test admin can delete (but will be blocked by dependencies)
        await self.test_rbac_admin_can_delete(recipes[0])
        
        print("\n🧪 Test 7: RBAC Enforcement - Manager Can Delete")
        print("-" * 50)
        
        # Test manager can delete (but will be blocked by dependencies)
        await self.test_rbac_manager_can_delete(recipes[0])
        
        print("\n🧪 Test 8: RBAC Enforcement - Staff Cannot Delete")
        print("-" * 50)
        
        # Test staff cannot delete
        await self.test_rbac_staff_cannot_delete(recipes[0])
        
        print("\n🧪 Cleanup")
        print("-" * 50)
        
        # Clean up test data
        await self.cleanup_test_data()
        
        # Print summary
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        
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
    async with RecipeDependenciesTester() as tester:
        await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())