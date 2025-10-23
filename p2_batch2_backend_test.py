#!/usr/bin/env python3
"""
Backend Testing for P2 Batch 2: Preparation Dependencies & Bulk Delete
Tests the preparation dependencies endpoint and enhanced delete functionality with RBAC.
"""

import requests
import json
import uuid
from datetime import datetime, timezone

# Configuration
BACKEND_URL = "https://resto-doc-scan.preview.emergentagent.com/api"

# Test credentials
ADMIN_CREDENTIALS = {"email": "admin@test.com", "password": "admin123"}
MANAGER_CREDENTIALS = {"email": "manager@test.com", "password": "manager123"}
STAFF_CREDENTIALS = {"email": "staff@test.com", "password": "staff123"}

class TestRunner:
    def __init__(self):
        self.admin_token = None
        self.manager_token = None
        self.staff_token = None
        self.test_data = {}
        self.passed = 0
        self.failed = 0
        
    def log(self, message):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        
    def assert_test(self, condition, test_name, details=""):
        if condition:
            self.passed += 1
            self.log(f"✅ PASS: {test_name}")
            if details:
                self.log(f"   {details}")
        else:
            self.failed += 1
            self.log(f"❌ FAIL: {test_name}")
            if details:
                self.log(f"   {details}")
                
    def login_user(self, credentials, role_name):
        """Login and return token"""
        try:
            response = requests.post(f"{BACKEND_URL}/auth/login", json=credentials)
            if response.status_code == 200:
                token = response.json()["access_token"]
                self.log(f"✅ {role_name} login successful")
                return token
            else:
                self.log(f"❌ {role_name} login failed: {response.status_code}")
                return None
        except Exception as e:
            self.log(f"❌ {role_name} login error: {str(e)}")
            return None
            
    def setup_auth(self):
        """Setup authentication for all user roles"""
        self.log("=== AUTHENTICATION SETUP ===")
        self.admin_token = self.login_user(ADMIN_CREDENTIALS, "Admin")
        self.manager_token = self.login_user(MANAGER_CREDENTIALS, "Manager")
        self.staff_token = self.login_user(STAFF_CREDENTIALS, "Staff")
        
        if not all([self.admin_token, self.manager_token, self.staff_token]):
            self.log("❌ Authentication setup failed - cannot proceed with tests")
            return False
        return True
        
    def create_test_ingredient(self, token, name, unit="kg", pack_cost=1000, pack_size=1.0):
        """Create a test ingredient"""
        ingredient_data = {
            "name": name,
            "unit": unit,
            "packSize": pack_size,
            "packCost": pack_cost,
            "minStockQty": 5.0,
            "category": "food",
            "wastePct": 5.0,
            "allergens": ["GLUTEN"] if "flour" in name.lower() else []
        }
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(f"{BACKEND_URL}/ingredients", json=ingredient_data, headers=headers)
        
        if response.status_code == 200:
            ingredient = response.json()
            self.log(f"✅ Created test ingredient: {name} (ID: {ingredient['id']})")
            return ingredient
        else:
            self.log(f"❌ Failed to create ingredient {name}: {response.status_code}")
            return None
            
    def create_test_preparation(self, token, name, ingredient_ids):
        """Create a test preparation using ingredients"""
        items = []
        for i, ing_id in enumerate(ingredient_ids):
            items.append({
                "ingredientId": ing_id,
                "qty": 0.5 + (i * 0.1),  # Varying quantities
                "unit": "kg"
            })
            
        prep_data = {
            "name": name,
            "items": items,
            "portions": 4,
            "instructions": f"Instructions for {name}"
        }
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(f"{BACKEND_URL}/preparations", json=prep_data, headers=headers)
        
        if response.status_code == 200:
            preparation = response.json()
            self.log(f"✅ Created test preparation: {name} (ID: {preparation['id']})")
            return preparation
        else:
            self.log(f"❌ Failed to create preparation {name}: {response.status_code}")
            return None
            
    def create_test_recipe(self, token, name, preparation_id):
        """Create a test recipe using a preparation"""
        recipe_data = {
            "name": name,
            "category": "main",
            "portions": 2,
            "targetFoodCostPct": 30.0,
            "price": 1500,  # €15.00 in cents
            "items": [
                {
                    "type": "preparation",
                    "itemId": preparation_id,
                    "qtyPerPortion": 1.0,
                    "unit": "portions"
                }
            ]
        }
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(f"{BACKEND_URL}/recipes", json=recipe_data, headers=headers)
        
        if response.status_code == 200:
            recipe = response.json()
            self.log(f"✅ Created test recipe: {name} (ID: {recipe['id']})")
            return recipe
        else:
            self.log(f"❌ Failed to create recipe {name}: {response.status_code}")
            return None
            
    def setup_test_data(self):
        """Create test data for dependency testing"""
        self.log("=== SETTING UP TEST DATA ===")
        
        # Create test ingredients
        flour = self.create_test_ingredient(self.admin_token, "Test Flour", "kg", 250, 1.0)
        tomatoes = self.create_test_ingredient(self.admin_token, "Test Tomatoes", "kg", 320, 1.0)
        cheese = self.create_test_ingredient(self.admin_token, "Test Mozzarella", "kg", 800, 1.0)
        
        if not all([flour, tomatoes, cheese]):
            return False
            
        self.test_data['ingredients'] = [flour, tomatoes, cheese]
        
        # Create test preparations
        # Preparation 1: Pizza Dough (will be used in recipe)
        pizza_dough = self.create_test_preparation(
            self.admin_token, 
            "Test Pizza Dough", 
            [flour['id'], tomatoes['id']]
        )
        
        # Preparation 2: Cheese Mix (will NOT be used in recipe)
        cheese_mix = self.create_test_preparation(
            self.admin_token,
            "Test Cheese Mix",
            [cheese['id']]
        )
        
        # Preparation 3: Base Sauce (will NOT be used in recipe)
        base_sauce = self.create_test_preparation(
            self.admin_token,
            "Test Base Sauce",
            [tomatoes['id']]
        )
        
        if not all([pizza_dough, cheese_mix, base_sauce]):
            return False
            
        self.test_data['preparations'] = [pizza_dough, cheese_mix, base_sauce]
        
        # Create a recipe that uses Pizza Dough preparation
        pizza_recipe = self.create_test_recipe(
            self.admin_token,
            "Test Pizza Margherita",
            pizza_dough['id']
        )
        
        if not pizza_recipe:
            return False
            
        self.test_data['recipe'] = pizza_recipe
        
        self.log(f"✅ Test data setup complete:")
        self.log(f"   - 3 ingredients created")
        self.log(f"   - 3 preparations created (1 with recipe dependency)")
        self.log(f"   - 1 recipe created using Pizza Dough preparation")
        
        return True
        
    def test_preparation_dependencies_endpoint(self):
        """Test GET /api/preparations/{id}/dependencies endpoint"""
        self.log("=== TESTING PREPARATION DEPENDENCIES ENDPOINT ===")
        
        pizza_dough = self.test_data['preparations'][0]  # Has recipe dependency
        cheese_mix = self.test_data['preparations'][1]   # No dependencies
        base_sauce = self.test_data['preparations'][2]   # No dependencies
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test 1: Preparation WITH recipe dependencies
        response = requests.get(f"{BACKEND_URL}/preparations/{pizza_dough['id']}/dependencies", headers=headers)
        self.assert_test(
            response.status_code == 200,
            "Dependencies endpoint returns 200 for preparation with recipes",
            f"Status: {response.status_code}"
        )
        
        if response.status_code == 200:
            data = response.json()
            self.assert_test(
                data.get('hasReferences') == True,
                "Preparation with recipe shows hasReferences=true",
                f"Response: {data}"
            )
            self.assert_test(
                data.get('references', {}).get('recipes', 0) == 1,
                "Preparation shows correct recipe count (1)",
                f"Recipe count: {data.get('references', {}).get('recipes', 0)}"
            )
            
        # Test 2: Preparation WITHOUT recipe dependencies
        response = requests.get(f"{BACKEND_URL}/preparations/{cheese_mix['id']}/dependencies", headers=headers)
        self.assert_test(
            response.status_code == 200,
            "Dependencies endpoint returns 200 for preparation without recipes",
            f"Status: {response.status_code}"
        )
        
        if response.status_code == 200:
            data = response.json()
            self.assert_test(
                data.get('hasReferences') == False,
                "Preparation without recipe shows hasReferences=false",
                f"Response: {data}"
            )
            self.assert_test(
                data.get('references', {}).get('recipes', 0) == 0,
                "Preparation shows correct recipe count (0)",
                f"Recipe count: {data.get('references', {}).get('recipes', 0)}"
            )
            
        # Test 3: Non-existent preparation
        fake_id = str(uuid.uuid4())
        response = requests.get(f"{BACKEND_URL}/preparations/{fake_id}/dependencies", headers=headers)
        # Note: The endpoint doesn't validate preparation existence, it just counts references
        self.assert_test(
            response.status_code == 200,
            "Dependencies endpoint handles non-existent preparation gracefully",
            f"Status: {response.status_code}"
        )
        
    def test_delete_endpoint_with_dependency_blocking(self):
        """Test DELETE /api/preparations/{id} with dependency validation"""
        self.log("=== TESTING DELETE ENDPOINT WITH DEPENDENCY BLOCKING ===")
        
        pizza_dough = self.test_data['preparations'][0]  # Has recipe dependency
        cheese_mix = self.test_data['preparations'][1]   # No dependencies
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test 1: Try to delete preparation WITH recipe dependencies (should fail)
        response = requests.delete(f"{BACKEND_URL}/preparations/{pizza_dough['id']}", headers=headers)
        self.assert_test(
            response.status_code == 400,
            "Delete preparation with recipe dependencies returns 400 error",
            f"Status: {response.status_code}"
        )
        
        if response.status_code == 400:
            error_data = response.json()
            error_message = error_data.get('detail', '')
            self.assert_test(
                'referenced in' in error_message and 'recipes' in error_message,
                "Error message mentions recipe references",
                f"Error: {error_message}"
            )
            self.assert_test(
                '1 recipes' in error_message,
                "Error message includes correct recipe count",
                f"Error: {error_message}"
            )
            
        # Test 2: Delete preparation WITHOUT dependencies (should succeed)
        response = requests.delete(f"{BACKEND_URL}/preparations/{cheese_mix['id']}", headers=headers)
        self.assert_test(
            response.status_code == 200,
            "Delete preparation without dependencies succeeds",
            f"Status: {response.status_code}"
        )
        
        if response.status_code == 200:
            # Verify preparation is actually deleted
            get_response = requests.get(f"{BACKEND_URL}/preparations/{cheese_mix['id']}", headers=headers)
            self.assert_test(
                get_response.status_code == 404,
                "Deleted preparation returns 404 when fetched",
                f"Status: {get_response.status_code}"
            )
            
    def test_rbac_enforcement_on_delete(self):
        """Test RBAC enforcement on DELETE /api/preparations/{id}"""
        self.log("=== TESTING RBAC ENFORCEMENT ON DELETE ===")
        
        base_sauce = self.test_data['preparations'][2]  # No dependencies, safe to delete
        
        # Test 1: Admin can delete (should succeed)
        admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        response = requests.delete(f"{BACKEND_URL}/preparations/{base_sauce['id']}", headers=admin_headers)
        self.assert_test(
            response.status_code == 200,
            "Admin can delete preparations",
            f"Status: {response.status_code}"
        )
        
        # Create another test preparation for manager test
        flour_id = self.test_data['ingredients'][0]['id']
        manager_test_prep = self.create_test_preparation(
            self.admin_token,
            "Manager Test Prep",
            [flour_id]
        )
        
        if manager_test_prep:
            # Test 2: Manager can delete (should succeed)
            manager_headers = {"Authorization": f"Bearer {self.manager_token}"}
            response = requests.delete(f"{BACKEND_URL}/preparations/{manager_test_prep['id']}", headers=manager_headers)
            self.assert_test(
                response.status_code == 200,
                "Manager can delete preparations",
                f"Status: {response.status_code}"
            )
            
        # Create another test preparation for staff test
        staff_test_prep = self.create_test_preparation(
            self.admin_token,
            "Staff Test Prep",
            [flour_id]
        )
        
        if staff_test_prep:
            # Test 3: Staff CANNOT delete (should fail with 403)
            staff_headers = {"Authorization": f"Bearer {self.staff_token}"}
            response = requests.delete(f"{BACKEND_URL}/preparations/{staff_test_prep['id']}", headers=staff_headers)
            self.assert_test(
                response.status_code == 403,
                "Staff cannot delete preparations (403 Forbidden)",
                f"Status: {response.status_code}"
            )
            
            if response.status_code == 403:
                error_data = response.json()
                error_message = error_data.get('detail', '')
                self.assert_test(
                    'Admin or Manager access required' in error_message,
                    "Error message indicates admin/manager access required",
                    f"Error: {error_message}"
                )
                
    def test_bulk_delete_scenario(self):
        """Test bulk delete scenario with mixed dependencies"""
        self.log("=== TESTING BULK DELETE SCENARIO ===")
        
        # Create 3 additional test preparations for bulk testing
        flour_id = self.test_data['ingredients'][0]['id']
        tomato_id = self.test_data['ingredients'][1]['id']
        
        bulk_prep_1 = self.create_test_preparation(self.admin_token, "Bulk Test Prep 1", [flour_id])
        bulk_prep_2 = self.create_test_preparation(self.admin_token, "Bulk Test Prep 2", [tomato_id])
        bulk_prep_3 = self.create_test_preparation(self.admin_token, "Bulk Test Prep 3", [flour_id, tomato_id])
        
        if not all([bulk_prep_1, bulk_prep_2, bulk_prep_3]):
            self.log("❌ Failed to create bulk test preparations")
            return
            
        # Create a recipe using bulk_prep_2 (this will create a dependency)
        recipe_with_dep = self.create_test_recipe(self.admin_token, "Bulk Test Recipe", bulk_prep_2['id'])
        
        if not recipe_with_dep:
            self.log("❌ Failed to create recipe for bulk test")
            return
            
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test dependencies for all 3 preparations
        # bulk_prep_1: No dependencies
        response = requests.get(f"{BACKEND_URL}/preparations/{bulk_prep_1['id']}/dependencies", headers=headers)
        if response.status_code == 200:
            data = response.json()
            self.assert_test(
                data.get('hasReferences') == False,
                "Bulk prep 1 has no dependencies",
                f"Dependencies: {data}"
            )
            
        # bulk_prep_2: Has recipe dependency
        response = requests.get(f"{BACKEND_URL}/preparations/{bulk_prep_2['id']}/dependencies", headers=headers)
        if response.status_code == 200:
            data = response.json()
            self.assert_test(
                data.get('hasReferences') == True and data.get('references', {}).get('recipes', 0) == 1,
                "Bulk prep 2 has recipe dependency",
                f"Dependencies: {data}"
            )
            
        # bulk_prep_3: No dependencies
        response = requests.get(f"{BACKEND_URL}/preparations/{bulk_prep_3['id']}/dependencies", headers=headers)
        if response.status_code == 200:
            data = response.json()
            self.assert_test(
                data.get('hasReferences') == False,
                "Bulk prep 3 has no dependencies",
                f"Dependencies: {data}"
            )
            
        # Attempt to delete preparation with dependency (should fail)
        response = requests.delete(f"{BACKEND_URL}/preparations/{bulk_prep_2['id']}", headers=headers)
        self.assert_test(
            response.status_code == 400,
            "Bulk delete: Preparation with recipe dependency blocked",
            f"Status: {response.status_code}"
        )
        
        # Delete preparations without dependencies (should succeed)
        response = requests.delete(f"{BACKEND_URL}/preparations/{bulk_prep_1['id']}", headers=headers)
        self.assert_test(
            response.status_code == 200,
            "Bulk delete: Preparation 1 without dependencies deleted successfully",
            f"Status: {response.status_code}"
        )
        
        response = requests.delete(f"{BACKEND_URL}/preparations/{bulk_prep_3['id']}", headers=headers)
        self.assert_test(
            response.status_code == 200,
            "Bulk delete: Preparation 3 without dependencies deleted successfully",
            f"Status: {response.status_code}"
        )
        
    def test_authentication_required(self):
        """Test that all endpoints require authentication"""
        self.log("=== TESTING AUTHENTICATION REQUIREMENTS ===")
        
        prep_id = self.test_data['preparations'][0]['id']
        
        # Test dependencies endpoint without auth
        response = requests.get(f"{BACKEND_URL}/preparations/{prep_id}/dependencies")
        self.assert_test(
            response.status_code in [401, 403],
            "Dependencies endpoint requires authentication",
            f"Status: {response.status_code}"
        )
        
        # Test delete endpoint without auth
        response = requests.delete(f"{BACKEND_URL}/preparations/{prep_id}")
        self.assert_test(
            response.status_code in [401, 403],
            "Delete endpoint requires authentication",
            f"Status: {response.status_code}"
        )
        
    def run_all_tests(self):
        """Run all test suites"""
        self.log("🧪 STARTING P2 BATCH 2: PREPARATION DEPENDENCIES & BULK DELETE BACKEND TESTING")
        self.log("=" * 80)
        
        # Setup
        if not self.setup_auth():
            return False
            
        if not self.setup_test_data():
            return False
            
        # Run test suites
        self.test_preparation_dependencies_endpoint()
        self.test_delete_endpoint_with_dependency_blocking()
        self.test_rbac_enforcement_on_delete()
        self.test_bulk_delete_scenario()
        self.test_authentication_required()
        
        # Summary
        self.log("=" * 80)
        self.log(f"🎯 TEST SUMMARY: {self.passed} PASSED, {self.failed} FAILED")
        
        if self.failed == 0:
            self.log("🏆 ALL TESTS PASSED - P2 BATCH 2 BACKEND IS FULLY FUNCTIONAL ✅")
        else:
            self.log(f"⚠️  {self.failed} TESTS FAILED - ISSUES NEED ATTENTION ❌")
            
        return self.failed == 0

if __name__ == "__main__":
    runner = TestRunner()
    success = runner.run_all_tests()
    exit(0 if success else 1)