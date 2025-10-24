#!/usr/bin/env python3
"""
P1 Bug #1: Receiving → Inventory Sync Test
Test that items received appear in Inventory afterward
"""

import requests
import json
from datetime import datetime, timezone

# Test Configuration
BASE_URL = "https://menuflow-8.preview.emergentagent.com/api"

# Test Credentials
TEST_CREDENTIALS = {
    "admin": {"email": "admin@test.com", "password": "admin123"},
    "manager": {"email": "manager@test.com", "password": "manager123"},
    "staff": {"email": "staff@test.com", "password": "staff123"}
}

class ReceivingInventorySyncTester:
    def __init__(self):
        self.auth_token = None
        self.user_data = None
        self.test_results = []
        
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
        return {"Authorization": f"Bearer {self.auth_token}"}
    
    def create_test_supplier(self):
        """Create a test supplier for receiving"""
        try:
            supplier_data = {
                "name": "Test Supplier for Receiving",
                "contacts": {
                    "name": "Test Contact",
                    "phone": "+39 02 1234567",
                    "email": "test@supplier.com"
                },
                "notes": "Test supplier for receiving sync test"
            }
            
            response = requests.post(
                f"{BASE_URL}/suppliers",
                json=supplier_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                supplier = response.json()
                self.log_result("Create Test Supplier", True, f"Created supplier: {supplier['name']}")
                return supplier
            else:
                self.log_result("Create Test Supplier", False, f"Failed: {response.status_code}", response.text)
                return None
        except Exception as e:
            self.log_result("Create Test Supplier", False, f"Error: {str(e)}")
            return None
    
    def create_test_ingredient(self):
        """Create a test ingredient for receiving"""
        try:
            ingredient_data = {
                "name": "Test Ingredient for Receiving",
                "unit": "kg",
                "packSize": 1.0,
                "packCost": 500,  # €5.00 in minor units
                "wastePct": 5.0,
                "allergens": ["GLUTEN"],
                "category": "food",
                "minStockQty": 10.0
            }
            
            response = requests.post(
                f"{BASE_URL}/ingredients",
                json=ingredient_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                ingredient = response.json()
                self.log_result("Create Test Ingredient", True, f"Created ingredient: {ingredient['name']}")
                return ingredient
            else:
                self.log_result("Create Test Ingredient", False, f"Failed: {response.status_code}", response.text)
                return None
        except Exception as e:
            self.log_result("Create Test Ingredient", False, f"Error: {str(e)}")
            return None
    
    def get_current_inventory_count(self, ingredient_id: str):
        """Get current inventory count for a specific ingredient"""
        try:
            response = requests.get(
                f"{BASE_URL}/inventory",
                headers=self.get_auth_headers()
            )
            
            if response.status_code == 200:
                inventory_items = response.json()
                
                # Find inventory record for this ingredient
                for item in inventory_items:
                    if item.get("ingredientId") == ingredient_id:
                        qty = item.get("qty") or item.get("qtyOnHand", 0)
                        self.log_result("Get Current Inventory", True, f"Found existing inventory: {qty} units")
                        return qty
                
                # No existing inventory record
                self.log_result("Get Current Inventory", True, "No existing inventory record found")
                return 0
            else:
                self.log_result("Get Current Inventory", False, f"Failed: {response.status_code}", response.text)
                return None
        except Exception as e:
            self.log_result("Get Current Inventory", False, f"Error: {str(e)}")
            return None
    
    def create_receiving_record(self, supplier_id: str, ingredient_id: str):
        """Create a new receiving record"""
        try:
            receiving_data = {
                "supplierId": supplier_id,
                "category": "food",
                "lines": [
                    {
                        "ingredientId": ingredient_id,
                        "description": "Test Item",
                        "qty": 10.0,
                        "unit": "kg",
                        "unitPrice": 500,  # €5.00 in minor units
                        "expiryDate": "2025-12-31"
                    }
                ],
                "arrivedAt": "2024-10-20",
                "notes": "Test receiving sync"
            }
            
            response = requests.post(
                f"{BASE_URL}/receiving",
                json=receiving_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                receiving = response.json()
                self.log_result("Create Receiving Record", True, f"Created receiving record: {receiving['id']}")
                return receiving
            else:
                self.log_result("Create Receiving Record", False, f"Failed: {response.status_code}", response.text)
                return None
        except Exception as e:
            self.log_result("Create Receiving Record", False, f"Error: {str(e)}")
            return None
    
    def verify_inventory_sync(self, ingredient_id: str, supplier_name: str, expected_qty: float):
        """Verify that inventory was updated after receiving"""
        try:
            response = requests.get(
                f"{BASE_URL}/inventory",
                headers=self.get_auth_headers()
            )
            
            if response.status_code == 200:
                inventory_items = response.json()
                
                # Find inventory record with countType="receiving"
                receiving_inventory = None
                for item in inventory_items:
                    if (item.get("ingredientId") == ingredient_id and 
                        item.get("countType") == "receiving"):
                        receiving_inventory = item
                        break
                
                if not receiving_inventory:
                    self.log_result("Verify Inventory Sync", False, "No inventory record with countType='receiving' found")
                    return False
                
                # Check quantity matches
                actual_qty = receiving_inventory.get("qty") or receiving_inventory.get("qtyOnHand", 0)
                if abs(actual_qty - expected_qty) < 0.01:
                    self.log_result("Verify Inventory Quantity", True, f"Correct quantity: {actual_qty}")
                else:
                    self.log_result("Verify Inventory Quantity", False, f"Expected {expected_qty}, got {actual_qty}")
                    return False
                
                # Check ingredientId matches
                if receiving_inventory.get("ingredientId") == ingredient_id:
                    self.log_result("Verify Inventory Ingredient ID", True, "Ingredient ID matches")
                else:
                    self.log_result("Verify Inventory Ingredient ID", False, f"Expected {ingredient_id}, got {receiving_inventory.get('ingredientId')}")
                    return False
                
                # Check location contains supplier name
                location = receiving_inventory.get("location", "")
                if supplier_name.lower() in location.lower():
                    self.log_result("Verify Inventory Location", True, f"Location contains supplier name: {location}")
                else:
                    self.log_result("Verify Inventory Location", False, f"Location '{location}' does not contain supplier name '{supplier_name}'")
                
                # Check for required fields (no null/missing fields)
                required_fields = ["id", "restaurantId", "ingredientId", "qty", "unit", "countType"]
                missing_fields = []
                for field in required_fields:
                    if field not in receiving_inventory or receiving_inventory[field] is None:
                        missing_fields.append(field)
                
                if missing_fields:
                    self.log_result("Verify Required Fields", False, f"Missing/null fields: {missing_fields}")
                    return False
                else:
                    self.log_result("Verify Required Fields", True, "All required fields present")
                
                self.log_result("Verify Inventory Sync", True, "Inventory sync successful - all checks passed")
                return True
                
            else:
                self.log_result("Verify Inventory Sync", False, f"Failed to get inventory: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_result("Verify Inventory Sync", False, f"Error: {str(e)}")
            return False
    
    def run_receiving_inventory_sync_test(self):
        """Run the complete P1 Bug test scenario"""
        print("🚀 Starting P1 Bug #1: Receiving → Inventory Sync Test")
        print("=" * 60)
        
        # Step 1: Login as admin
        if not self.authenticate("admin"):
            print("❌ Authentication failed - cannot continue test")
            return False
        
        # Step 2: Create test supplier
        supplier = self.create_test_supplier()
        if not supplier:
            print("❌ Failed to create test supplier - cannot continue")
            return False
        
        # Step 3: Create test ingredient
        ingredient = self.create_test_ingredient()
        if not ingredient:
            print("❌ Failed to create test ingredient - cannot continue")
            return False
        
        # Step 4: Get current inventory count
        initial_count = self.get_current_inventory_count(ingredient["id"])
        if initial_count is None:
            print("❌ Failed to get current inventory count - cannot continue")
            return False
        
        # Step 5: Create receiving record
        receiving = self.create_receiving_record(supplier["id"], ingredient["id"])
        if not receiving:
            print("❌ Failed to create receiving record - BUG CONFIRMED")
            return False
        
        # Step 6: Immediately verify inventory sync
        expected_qty = 10.0  # From receiving line qty
        sync_success = self.verify_inventory_sync(ingredient["id"], supplier["name"], expected_qty)
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed_tests = sum(1 for result in self.test_results if result["success"])
        total_tests = len(self.test_results)
        
        print(f"Tests Passed: {passed_tests}/{total_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if sync_success:
            print("\n✅ P1 BUG STATUS: NOT REPRODUCED")
            print("   Receiving → Inventory sync is working correctly")
        else:
            print("\n❌ P1 BUG STATUS: CONFIRMED")
            print("   Items received do NOT appear in Inventory")
        
        # Show failed tests
        failed_tests = [result for result in self.test_results if not result["success"]]
        if failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"   - {test['test']}: {test['message']}")
        
        return sync_success

def main():
    """Main test execution"""
    tester = ReceivingInventorySyncTester()
    success = tester.run_receiving_inventory_sync_test()
    
    if success:
        print("\n🎉 All tests passed - Bug not reproduced")
        exit(0)
    else:
        print("\n💥 Bug confirmed - Receiving → Inventory sync is broken")
        exit(1)

if __name__ == "__main__":
    main()