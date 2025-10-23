#!/usr/bin/env python3
"""
P1 Fixes Testing: Preparations Portions + Instructions Persistence
Tests for portions field validation and instructions persistence in preparations and recipes
"""

import requests
import json
from datetime import datetime

# Test Configuration
BASE_URL = "https://allergen-taxonomy.preview.emergentagent.com/api"

# Test Credentials
TEST_CREDENTIALS = {
    "admin": {"email": "admin@test.com", "password": "admin123"},
    "manager": {"email": "manager@test.com", "password": "manager123"},
    "staff": {"email": "staff@test.com", "password": "staff123"}
}

class P1FixesTester:
    def __init__(self):
        self.auth_token = None
        self.user_data = None
        self.test_results = []
        self.test_data = {}
        
    def log_result(self, test_name: str, success: bool, message: str, details=None):
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
    
    def authenticate(self, user_type: str = "admin") -> bool:
        """Authenticate with the backend"""
        try:
            credentials = TEST_CREDENTIALS[user_type]
            
            response = requests.post(
                f"{BASE_URL}/auth/login",
                json=credentials,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data["access_token"]
                self.user_data = data["user"]
                self.log_result("Authentication", True, f"Logged in as {user_type}")
                return True
            else:
                self.log_result("Authentication", False, f"Login failed: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_result("Authentication", False, f"Login error: {str(e)}")
            return False
    
    def get_auth_headers(self):
        """Get authorization headers"""
        return {"Authorization": f"Bearer {self.auth_token}", "Content-Type": "application/json"}
    
    def create_test_ingredients(self):
        """Create test ingredients for preparations"""
        ingredients_data = [
            {
                "name": "Test Flour",
                "unit": "kg",
                "packSize": 1.0,
                "packCost": 2.50,
                "wastePct": 5.0,
                "allergens": ["GLUTEN"],
                "category": "food"
            },
            {
                "name": "Test Tomatoes",
                "unit": "kg", 
                "packSize": 1.0,
                "packCost": 3.20,
                "wastePct": 15.0,
                "allergens": [],
                "category": "food"
            }
        ]
        
        created_ingredients = []
        
        for ingredient_data in ingredients_data:
            try:
                response = requests.post(
                    f"{BASE_URL}/ingredients",
                    json=ingredient_data,
                    headers=self.get_auth_headers()
                )
                
                if response.status_code == 200:
                    ingredient = response.json()
                    created_ingredients.append(ingredient)
                    self.log_result("Create Test Ingredient", True, f"Created {ingredient['name']}")
                else:
                    self.log_result("Create Test Ingredient", False, f"Failed to create {ingredient_data['name']}: {response.status_code}", response.text)
            except Exception as e:
                self.log_result("Create Test Ingredient", False, f"Error creating {ingredient_data['name']}: {str(e)}")
        
        return created_ingredients
    
    def test_preparation_portions_valid(self, ingredients):
        """Test preparation creation with valid portions=12"""
        if len(ingredients) < 2:
            self.log_result("Preparation Portions Valid", False, "Not enough ingredients available")
            return None
        
        prep_data = {
            "name": "Test Preparation with Portions",
            "items": [
                {
                    "ingredientId": ingredients[0]["id"],
                    "qty": 0.5,
                    "unit": "kg"
                },
                {
                    "ingredientId": ingredients[1]["id"],
                    "qty": 0.3,
                    "unit": "kg"
                }
            ],
            "portions": 12,  # Valid portions
            "instructions": "Mix ingredients well\nBake at 180°C for 30 minutes"
        }
        
        try:
            response = requests.post(
                f"{BASE_URL}/preparations",
                json=prep_data,
                headers=self.get_auth_headers()
            )
            
            if response.status_code == 200:
                preparation = response.json()
                
                # Verify portions field is stored correctly
                if preparation.get("portions") == 12:
                    self.log_result("Preparation Portions Valid", True, "Preparation created with portions=12")
                    return preparation
                else:
                    self.log_result("Preparation Portions Valid", False, f"Expected portions=12, got {preparation.get('portions')}")
                    return None
            else:
                self.log_result("Preparation Portions Valid", False, f"Failed: {response.status_code}", response.text)
                return None
        except Exception as e:
            self.log_result("Preparation Portions Valid", False, f"Error: {str(e)}")
            return None
    
    def test_preparation_portions_persistence(self, preparation_id):
        """Test that portions field persists in DB and GET returns it"""
        try:
            response = requests.get(
                f"{BASE_URL}/preparations/{preparation_id}",
                headers=self.get_auth_headers()
            )
            
            if response.status_code == 200:
                preparation = response.json()
                
                if preparation.get("portions") == 12:
                    self.log_result("Preparation Portions Persistence", True, "GET preparation returns portions=12 correctly")
                    return True
                else:
                    self.log_result("Preparation Portions Persistence", False, f"Expected portions=12, got {preparation.get('portions')}")
                    return False
            else:
                self.log_result("Preparation Portions Persistence", False, f"Failed to GET preparation: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_result("Preparation Portions Persistence", False, f"Error: {str(e)}")
            return False
    
    def test_preparation_portions_update(self, preparation_id):
        """Test updating portions to 8 and verify persistence"""
        try:
            update_data = {
                "portions": 8
            }
            
            response = requests.put(
                f"{BASE_URL}/preparations/{preparation_id}",
                json=update_data,
                headers=self.get_auth_headers()
            )
            
            if response.status_code == 200:
                updated_prep = response.json()
                
                if updated_prep.get("portions") == 8:
                    self.log_result("Preparation Portions Update", True, "Updated portions to 8 successfully")
                    
                    # Verify persistence with GET
                    get_response = requests.get(
                        f"{BASE_URL}/preparations/{preparation_id}",
                        headers=self.get_auth_headers()
                    )
                    
                    if get_response.status_code == 200:
                        retrieved_prep = get_response.json()
                        if retrieved_prep.get("portions") == 8:
                            self.log_result("Preparation Portions Update Persistence", True, "Updated portions=8 persists correctly")
                            return True
                        else:
                            self.log_result("Preparation Portions Update Persistence", False, f"Expected portions=8, got {retrieved_prep.get('portions')}")
                            return False
                    else:
                        self.log_result("Preparation Portions Update Persistence", False, f"Failed to verify update: {get_response.status_code}")
                        return False
                else:
                    self.log_result("Preparation Portions Update", False, f"Expected portions=8, got {updated_prep.get('portions')}")
                    return False
            else:
                self.log_result("Preparation Portions Update", False, f"Failed: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_result("Preparation Portions Update", False, f"Error: {str(e)}")
            return False
    
    def test_preparation_portions_invalid_values(self, ingredients):
        """Test invalid portions values: 0, -1, 1.5 (should return 422)"""
        if len(ingredients) < 2:
            self.log_result("Preparation Portions Invalid", False, "Not enough ingredients available")
            return
        
        invalid_values = [0, -1, 1.5]
        
        for invalid_portions in invalid_values:
            prep_data = {
                "name": f"Test Preparation Invalid Portions {invalid_portions}",
                "items": [
                    {
                        "ingredientId": ingredients[0]["id"],
                        "qty": 0.5,
                        "unit": "kg"
                    }
                ],
                "portions": invalid_portions
            }
            
            try:
                response = requests.post(
                    f"{BASE_URL}/preparations",
                    json=prep_data,
                    headers=self.get_auth_headers()
                )
                
                if response.status_code == 422:
                    self.log_result(f"Preparation Portions Invalid ({invalid_portions})", True, f"Correctly rejected portions={invalid_portions} with 422")
                else:
                    self.log_result(f"Preparation Portions Invalid ({invalid_portions})", False, f"Should reject portions={invalid_portions}: {response.status_code}", response.text)
            except Exception as e:
                self.log_result(f"Preparation Portions Invalid ({invalid_portions})", False, f"Error: {str(e)}")
    
    def test_preparation_instructions_persistence(self, ingredients):
        """Test instructions field persistence with multi-line content"""
        if len(ingredients) < 2:
            self.log_result("Preparation Instructions Persistence", False, "Not enough ingredients available")
            return None
        
        # Multi-line instructions with special characters
        test_instructions = "Mix ingredients well\nBake at 180°C for 30 minutes"
        
        prep_data = {
            "name": "Test Preparation Instructions",
            "items": [
                {
                    "ingredientId": ingredients[0]["id"],
                    "qty": 0.5,
                    "unit": "kg"
                },
                {
                    "ingredientId": ingredients[1]["id"],
                    "qty": 0.3,
                    "unit": "kg"
                }
            ],
            "portions": 4,
            "instructions": test_instructions
        }
        
        try:
            # Create preparation
            response = requests.post(
                f"{BASE_URL}/preparations",
                json=prep_data,
                headers=self.get_auth_headers()
            )
            
            if response.status_code == 200:
                preparation = response.json()
                
                # Verify instructions are stored exactly
                if preparation.get("instructions") == test_instructions:
                    self.log_result("Preparation Instructions Create", True, "Instructions stored exactly (no trimming, supports multi-line)")
                    
                    # Verify persistence with GET
                    get_response = requests.get(
                        f"{BASE_URL}/preparations/{preparation['id']}",
                        headers=self.get_auth_headers()
                    )
                    
                    if get_response.status_code == 200:
                        retrieved_prep = get_response.json()
                        if retrieved_prep.get("instructions") == test_instructions:
                            self.log_result("Preparation Instructions GET", True, "GET returns instructions unchanged")
                            return preparation
                        else:
                            self.log_result("Preparation Instructions GET", False, f"Instructions changed: expected '{test_instructions}', got '{retrieved_prep.get('instructions')}'")
                            return None
                    else:
                        self.log_result("Preparation Instructions GET", False, f"Failed to GET preparation: {get_response.status_code}")
                        return None
                else:
                    self.log_result("Preparation Instructions Create", False, f"Instructions changed: expected '{test_instructions}', got '{preparation.get('instructions')}'")
                    return None
            else:
                self.log_result("Preparation Instructions Create", False, f"Failed: {response.status_code}", response.text)
                return None
        except Exception as e:
            self.log_result("Preparation Instructions Create", False, f"Error: {str(e)}")
            return None
    
    def test_preparation_instructions_update(self, preparation_id):
        """Test updating instructions and verify persistence"""
        new_instructions = "Updated instructions\nStep 1: New process\nStep 2: Final step"
        
        try:
            update_data = {
                "instructions": new_instructions
            }
            
            response = requests.put(
                f"{BASE_URL}/preparations/{preparation_id}",
                json=update_data,
                headers=self.get_auth_headers()
            )
            
            if response.status_code == 200:
                updated_prep = response.json()
                
                if updated_prep.get("instructions") == new_instructions:
                    self.log_result("Preparation Instructions Update", True, "Instructions updated successfully")
                    
                    # Verify persistence with GET
                    get_response = requests.get(
                        f"{BASE_URL}/preparations/{preparation_id}",
                        headers=self.get_auth_headers()
                    )
                    
                    if get_response.status_code == 200:
                        retrieved_prep = get_response.json()
                        if retrieved_prep.get("instructions") == new_instructions:
                            self.log_result("Preparation Instructions Update Persistence", True, "Updated instructions persist correctly")
                            return True
                        else:
                            self.log_result("Preparation Instructions Update Persistence", False, f"Instructions changed after update")
                            return False
                    else:
                        self.log_result("Preparation Instructions Update Persistence", False, f"Failed to verify update: {get_response.status_code}")
                        return False
                else:
                    self.log_result("Preparation Instructions Update", False, f"Instructions not updated correctly")
                    return False
            else:
                self.log_result("Preparation Instructions Update", False, f"Failed: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_result("Preparation Instructions Update", False, f"Error: {str(e)}")
            return False
    
    def test_recipe_instructions_persistence(self, ingredients):
        """Test recipe instructions field persistence"""
        if len(ingredients) < 2:
            self.log_result("Recipe Instructions Persistence", False, "Not enough ingredients available")
            return None
        
        # Multi-line recipe instructions
        test_instructions = "Step 1: Prepare base\nStep 2: Add toppings\nStep 3: Cook"
        
        recipe_data = {
            "name": "Test Recipe Instructions",
            "category": "test",
            "portions": 4,
            "targetFoodCostPct": 25.0,
            "price": 1000,  # €10.00 in minor units
            "items": [
                {
                    "type": "ingredient",
                    "itemId": ingredients[0]["id"],
                    "qtyPerPortion": 0.1,
                    "unit": "kg"
                },
                {
                    "type": "ingredient",
                    "itemId": ingredients[1]["id"],
                    "qtyPerPortion": 0.05,
                    "unit": "kg"
                }
            ],
            "instructions": test_instructions
        }
        
        try:
            # Create recipe
            response = requests.post(
                f"{BASE_URL}/recipes",
                json=recipe_data,
                headers=self.get_auth_headers()
            )
            
            if response.status_code == 200:
                recipe = response.json()
                
                # Verify instructions are stored exactly
                if recipe.get("instructions") == test_instructions:
                    self.log_result("Recipe Instructions Create", True, "Recipe instructions stored exactly")
                    
                    # Verify persistence with GET
                    get_response = requests.get(
                        f"{BASE_URL}/recipes/{recipe['id']}",
                        headers=self.get_auth_headers()
                    )
                    
                    if get_response.status_code == 200:
                        retrieved_recipe = get_response.json()
                        if retrieved_recipe.get("instructions") == test_instructions:
                            self.log_result("Recipe Instructions GET", True, "GET returns recipe instructions unchanged")
                            return recipe
                        else:
                            self.log_result("Recipe Instructions GET", False, f"Instructions changed: expected '{test_instructions}', got '{retrieved_recipe.get('instructions')}'")
                            return None
                    else:
                        self.log_result("Recipe Instructions GET", False, f"Failed to GET recipe: {get_response.status_code}")
                        return None
                else:
                    self.log_result("Recipe Instructions Create", False, f"Instructions changed: expected '{test_instructions}', got '{recipe.get('instructions')}'")
                    return None
            else:
                self.log_result("Recipe Instructions Create", False, f"Failed: {response.status_code}", response.text)
                return None
        except Exception as e:
            self.log_result("Recipe Instructions Create", False, f"Error: {str(e)}")
            return None
    
    def test_recipe_instructions_update(self, recipe_id):
        """Test updating recipe instructions and verify persistence"""
        new_instructions = "Updated recipe steps\nStep A: New method\nStep B: Different approach\nStep C: Final result"
        
        try:
            update_data = {
                "instructions": new_instructions
            }
            
            response = requests.put(
                f"{BASE_URL}/recipes/{recipe_id}",
                json=update_data,
                headers=self.get_auth_headers()
            )
            
            if response.status_code == 200:
                updated_recipe = response.json()
                
                if updated_recipe.get("instructions") == new_instructions:
                    self.log_result("Recipe Instructions Update", True, "Recipe instructions updated successfully")
                    
                    # Verify persistence with GET
                    get_response = requests.get(
                        f"{BASE_URL}/recipes/{recipe_id}",
                        headers=self.get_auth_headers()
                    )
                    
                    if get_response.status_code == 200:
                        retrieved_recipe = get_response.json()
                        if retrieved_recipe.get("instructions") == new_instructions:
                            self.log_result("Recipe Instructions Update Persistence", True, "Updated recipe instructions persist correctly")
                            return True
                        else:
                            self.log_result("Recipe Instructions Update Persistence", False, f"Instructions changed after update")
                            return False
                    else:
                        self.log_result("Recipe Instructions Update Persistence", False, f"Failed to verify update: {get_response.status_code}")
                        return False
                else:
                    self.log_result("Recipe Instructions Update", False, f"Instructions not updated correctly")
                    return False
            else:
                self.log_result("Recipe Instructions Update", False, f"Failed: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_result("Recipe Instructions Update", False, f"Error: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all P1 fixes tests"""
        print("🚀 Starting P1 Fixes Testing: Preparations Portions + Instructions Persistence")
        print("=" * 80)
        
        # Authenticate as admin
        if not self.authenticate("admin"):
            print("❌ Authentication failed - cannot continue tests")
            return
        
        print("\n🥘 Setting Up Test Data")
        print("-" * 40)
        
        # Create test ingredients
        ingredients = self.create_test_ingredients()
        if len(ingredients) < 2:
            print("❌ Failed to create required test ingredients - cannot continue")
            return
        
        print("\n📊 Testing Preparations - Portions Field")
        print("-" * 40)
        
        # Test 1: Create preparation with portions=12
        preparation = self.test_preparation_portions_valid(ingredients)
        
        if preparation:
            # Test 2: Verify portions persists in DB and GET returns it
            self.test_preparation_portions_persistence(preparation["id"])
            
            # Test 3: Update portions to 8 and verify persistence
            self.test_preparation_portions_update(preparation["id"])
        
        # Test 4: Try invalid values (0, -1, 1.5) - should return 422
        self.test_preparation_portions_invalid_values(ingredients)
        
        print("\n📝 Testing Preparations - Instructions Persistence")
        print("-" * 40)
        
        # Test 5: Create preparation with multi-line instructions and verify persistence
        prep_with_instructions = self.test_preparation_instructions_persistence(ingredients)
        
        if prep_with_instructions:
            # Test 6: Update instructions and verify persistence
            self.test_preparation_instructions_update(prep_with_instructions["id"])
        
        print("\n🍽️ Testing Recipes - Instructions Persistence")
        print("-" * 40)
        
        # Test 7: Create recipe with multi-line instructions and verify persistence
        recipe_with_instructions = self.test_recipe_instructions_persistence(ingredients)
        
        if recipe_with_instructions:
            # Test 8: Update recipe instructions and verify persistence
            self.test_recipe_instructions_update(recipe_with_instructions["id"])
        
        # Print summary
        print("\n📊 TEST SUMMARY")
        print("=" * 50)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        # Show failed tests
        failed_tests = [result for result in self.test_results if not result["success"]]
        if failed_tests:
            print(f"\n❌ FAILED TESTS ({len(failed_tests)}):")
            for test in failed_tests:
                print(f"  - {test['test']}: {test['message']}")
        else:
            print(f"\n🎉 ALL TESTS PASSED!")
        
        return self.test_results

def main():
    """Main function to run P1 fixes tests"""
    tester = P1FixesTester()
    results = tester.run_all_tests()
    
    # Return exit code based on results
    failed_count = sum(1 for result in results if not result["success"])
    return 0 if failed_count == 0 else 1

if __name__ == "__main__":
    exit(main())