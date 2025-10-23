#!/usr/bin/env python3
"""
Backend Test Suite for P2 Batch 5: Inventory Bulk Delete Backend (FINAL BATCH)
Tests the inventory dependencies endpoint and delete functionality with master ingredient preservation.
"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Any

# Configuration
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL', 'https://resto-doc-scan.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

# Test credentials
TEST_USERS = {
    "admin": {"email": "admin@test.com", "password": "admin123"},
    "manager": {"email": "manager@test.com", "password": "manager123"},
    "staff": {"email": "staff@test.com", "password": "staff123"}
}

class InventoryBulkDeleteTester:
    def __init__(self):
        self.session = None
        self.tokens = {}
        self.test_data = {
            "ingredients": [],
            "inventory_records": []
        }
        self.results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": []
        }

    async def setup_session(self):
        """Initialize HTTP session"""
        connector = aiohttp.TCPConnector(ssl=False)
        self.session = aiohttp.ClientSession(connector=connector)

    async def cleanup_session(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()

    async def authenticate_users(self):
        """Authenticate all test users"""
        print("🔐 Authenticating test users...")
        
        for role, credentials in TEST_USERS.items():
            try:
                async with self.session.post(
                    f"{API_BASE}/auth/login",
                    json=credentials
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.tokens[role] = data["access_token"]
                        print(f"✅ {role.capitalize()} authenticated successfully")
                    else:
                        error_text = await response.text()
                        print(f"❌ {role.capitalize()} authentication failed: {response.status} - {error_text}")
                        return False
            except Exception as e:
                print(f"❌ {role.capitalize()} authentication error: {str(e)}")
                return False
        
        return True

    async def make_request(self, method: str, endpoint: str, role: str = "admin", **kwargs):
        """Make authenticated API request"""
        headers = kwargs.get("headers", {})
        if role in self.tokens:
            headers["Authorization"] = f"Bearer {self.tokens[role]}"
        kwargs["headers"] = headers
        
        async with self.session.request(method, f"{API_BASE}{endpoint}", **kwargs) as response:
            try:
                data = await response.json()
            except:
                data = await response.text()
            return response.status, data

    def log_test(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        self.results["total_tests"] += 1
        if passed:
            self.results["passed"] += 1
            print(f"✅ {test_name}")
        else:
            self.results["failed"] += 1
            self.results["errors"].append(f"{test_name}: {details}")
            print(f"❌ {test_name}: {details}")

    async def create_test_ingredients(self):
        """Create test ingredients for inventory testing"""
        print("\n📦 Creating test ingredients...")
        
        test_ingredients = [
            {
                "name": "Test Flour for Inventory",
                "unit": "kg",
                "packSize": 25.0,
                "packCost": 15.50,
                "category": "food",
                "wastePct": 5.0,
                "minStockQty": 10.0,
                "allergens": ["GLUTEN"]
            },
            {
                "name": "Test Tomatoes for Inventory", 
                "unit": "kg",
                "packSize": 5.0,
                "packCost": 12.00,
                "category": "food",
                "wastePct": 15.0,
                "minStockQty": 5.0,
                "allergens": []
            },
            {
                "name": "Test Olive Oil for Inventory",
                "unit": "l",
                "packSize": 1.0,
                "packCost": 8.50,
                "category": "food", 
                "wastePct": 2.0,
                "minStockQty": 2.0,
                "allergens": []
            }
        ]
        
        for ingredient_data in test_ingredients:
            status, data = await self.make_request("POST", "/ingredients", json=ingredient_data)
            if status in [200, 201]:
                self.test_data["ingredients"].append(data)
                print(f"✅ Created ingredient: {data['name']} (ID: {data['id']})")
            else:
                print(f"❌ Failed to create ingredient {ingredient_data['name']}: {status} - {data}")
                return False
        
        return True

    async def create_test_inventory_records(self):
        """Create test inventory records"""
        print("\n📋 Creating test inventory records...")
        
        for i, ingredient in enumerate(self.test_data["ingredients"]):
            inventory_data = {
                "ingredientId": ingredient["id"],
                "qty": 50.0 + (i * 10),  # Different quantities
                "unit": ingredient["unit"],
                "countType": "physical",
                "location": f"Storage Area {i+1}",
                "batchExpiry": "2025-12-31"
            }
            
            status, data = await self.make_request("POST", "/inventory", json=inventory_data)
            if status in [200, 201]:
                self.test_data["inventory_records"].append(data)
                print(f"✅ Created inventory record: {data['qty']} {data['unit']} of {ingredient['name']} (ID: {data['id']})")
            else:
                print(f"❌ Failed to create inventory record for {ingredient['name']}: {status} - {data}")
                return False
        
        return True

    async def test_inventory_dependencies_endpoint(self):
        """Test GET /api/inventory/{id}/dependencies endpoint"""
        print("\n🔍 Testing Inventory Dependencies Endpoint...")
        
        # Test 1: Dependencies for existing inventory record
        if self.test_data["inventory_records"]:
            inventory_id = self.test_data["inventory_records"][0]["id"]
            status, data = await self.make_request("GET", f"/inventory/{inventory_id}/dependencies")
            
            expected_structure = {"hasReferences", "canDelete", "references", "message"}
            if status == 200 and all(key in data for key in expected_structure):
                if data["canDelete"] is True and data["hasReferences"] is False:
                    self.log_test("Dependencies endpoint returns canDelete=true for existing inventory", True)
                else:
                    self.log_test("Dependencies endpoint returns canDelete=true for existing inventory", False, 
                                f"Expected canDelete=true, hasReferences=false, got canDelete={data.get('canDelete')}, hasReferences={data.get('hasReferences')}")
            else:
                self.log_test("Dependencies endpoint returns correct structure", False, 
                            f"Status: {status}, Missing keys: {expected_structure - set(data.keys()) if isinstance(data, dict) else 'Invalid response'}")
        
        # Test 2: Dependencies for non-existent inventory record
        fake_id = "non-existent-inventory-id"
        status, data = await self.make_request("GET", f"/inventory/{fake_id}/dependencies")
        
        if status == 200 and isinstance(data, dict):
            if data.get("canDelete") is False and "not found" in data.get("message", "").lower():
                self.log_test("Dependencies endpoint returns canDelete=false for non-existent inventory", True)
            else:
                self.log_test("Dependencies endpoint returns canDelete=false for non-existent inventory", False,
                            f"Expected canDelete=false with 'not found' message, got: {data}")
        else:
            self.log_test("Dependencies endpoint handles non-existent inventory", False, f"Status: {status}, Data: {data}")

    async def test_delete_endpoint_with_ingredient_preservation(self):
        """Test DELETE /api/inventory/{id} - CRITICAL: Master ingredient preservation"""
        print("\n🗑️ Testing Delete Endpoint with Master Ingredient Preservation...")
        
        if not self.test_data["inventory_records"] or not self.test_data["ingredients"]:
            self.log_test("Delete endpoint test setup", False, "No test data available")
            return
        
        # Get first inventory record and its ingredient
        inventory_record = self.test_data["inventory_records"][0]
        ingredient_id = inventory_record["ingredientId"]
        inventory_id = inventory_record["id"]
        
        # Test 1: Verify ingredient exists before deletion
        status, ingredient_before = await self.make_request("GET", f"/ingredients/{ingredient_id}")
        if status != 200:
            self.log_test("Ingredient exists before inventory deletion", False, f"Ingredient not found: {status}")
            return
        
        self.log_test("Ingredient exists before inventory deletion", True)
        
        # Test 2: Delete inventory record (admin)
        status, data = await self.make_request("DELETE", f"/inventory/{inventory_id}", role="admin")
        if status == 200:
            self.log_test("Admin can delete inventory record", True)
        else:
            self.log_test("Admin can delete inventory record", False, f"Status: {status}, Data: {data}")
            return
        
        # Test 3: CRITICAL - Verify inventory record is deleted
        status, data = await self.make_request("GET", f"/inventory")
        remaining_inventory = [inv for inv in data if inv["id"] == inventory_id] if isinstance(data, list) else []
        
        if len(remaining_inventory) == 0:
            self.log_test("Inventory record successfully deleted", True)
        else:
            self.log_test("Inventory record successfully deleted", False, "Inventory record still exists")
        
        # Test 4: CRITICAL - Verify master ingredient still exists (NOT deleted)
        status, ingredient_after = await self.make_request("GET", f"/ingredients/{ingredient_id}")
        if status == 200 and ingredient_after.get("id") == ingredient_id:
            self.log_test("Master ingredient preserved after inventory deletion", True)
        else:
            self.log_test("Master ingredient preserved after inventory deletion", False, 
                        f"Ingredient deleted or not found: Status {status}")

    async def test_rbac_enforcement(self):
        """Test RBAC enforcement on delete operations"""
        print("\n🔐 Testing RBAC Enforcement...")
        
        if len(self.test_data["inventory_records"]) < 2:
            self.log_test("RBAC test setup", False, "Insufficient inventory records for RBAC testing")
            return
        
        # Test 1: Manager can delete (NEW FEATURE)
        inventory_id = self.test_data["inventory_records"][1]["id"]
        status, data = await self.make_request("DELETE", f"/inventory/{inventory_id}", role="manager")
        
        if status == 200:
            self.log_test("Manager can delete inventory records", True)
        else:
            self.log_test("Manager can delete inventory records", False, f"Status: {status}, Data: {data}")
        
        # Test 2: Staff CANNOT delete (should return 403)
        if len(self.test_data["inventory_records"]) >= 3:
            inventory_id = self.test_data["inventory_records"][2]["id"]
            status, data = await self.make_request("DELETE", f"/inventory/{inventory_id}", role="staff")
            
            if status == 403:
                self.log_test("Staff cannot delete inventory records (403 Forbidden)", True)
            else:
                self.log_test("Staff cannot delete inventory records (403 Forbidden)", False, 
                            f"Expected 403, got {status}: {data}")

    async def test_bulk_delete_scenario(self):
        """Test bulk delete scenario with master ingredient preservation"""
        print("\n🔄 Testing Bulk Delete Scenario...")
        
        # Create additional inventory records for bulk testing
        print("Creating additional inventory records for bulk testing...")
        additional_inventory = []
        
        for i, ingredient in enumerate(self.test_data["ingredients"]):
            # Create second inventory record for each ingredient
            inventory_data = {
                "ingredientId": ingredient["id"],
                "qty": 25.0 + (i * 5),
                "unit": ingredient["unit"],
                "countType": "physical",
                "location": f"Bulk Test Area {i+1}",
                "batchExpiry": "2025-11-30"
            }
            
            status, data = await self.make_request("POST", "/inventory", json=inventory_data)
            if status == 201:
                additional_inventory.append(data)
        
        # Verify all ingredients exist before bulk delete
        all_ingredients_exist = True
        for ingredient in self.test_data["ingredients"]:
            status, data = await self.make_request("GET", f"/ingredients/{ingredient['id']}")
            if status != 200:
                all_ingredients_exist = False
                break
        
        self.log_test("All ingredients exist before bulk delete", all_ingredients_exist)
        
        # Perform bulk delete on additional inventory records
        deleted_count = 0
        for inventory in additional_inventory:
            status, data = await self.make_request("DELETE", f"/inventory/{inventory['id']}", role="admin")
            if status == 200:
                deleted_count += 1
        
        self.log_test(f"Bulk delete of {len(additional_inventory)} inventory records", 
                     deleted_count == len(additional_inventory),
                     f"Deleted {deleted_count}/{len(additional_inventory)} records")
        
        # CRITICAL: Verify all master ingredients still exist after bulk delete
        all_ingredients_preserved = True
        for ingredient in self.test_data["ingredients"]:
            status, data = await self.make_request("GET", f"/ingredients/{ingredient['id']}")
            if status != 200:
                all_ingredients_preserved = False
                break
        
        self.log_test("All master ingredients preserved after bulk delete", all_ingredients_preserved)

    async def test_non_existent_inventory_delete(self):
        """Test delete of non-existent inventory record"""
        print("\n🚫 Testing Non-existent Inventory Delete...")
        
        fake_id = "non-existent-inventory-record-id"
        status, data = await self.make_request("DELETE", f"/inventory/{fake_id}", role="admin")
        
        if status == 404:
            self.log_test("Delete non-existent inventory returns 404", True)
        else:
            self.log_test("Delete non-existent inventory returns 404", False, 
                        f"Expected 404, got {status}: {data}")

    async def cleanup_test_data(self):
        """Clean up test data"""
        print("\n🧹 Cleaning up test data...")
        
        # Delete remaining inventory records
        for inventory in self.test_data["inventory_records"]:
            try:
                await self.make_request("DELETE", f"/inventory/{inventory['id']}", role="admin")
            except:
                pass
        
        # Delete test ingredients
        for ingredient in self.test_data["ingredients"]:
            try:
                await self.make_request("DELETE", f"/ingredients/{ingredient['id']}", role="admin")
            except:
                pass

    async def run_all_tests(self):
        """Run comprehensive inventory bulk delete tests"""
        print("🧪 P2 BATCH 5: INVENTORY BULK DELETE BACKEND TESTING")
        print("=" * 60)
        
        try:
            await self.setup_session()
            
            # Authentication
            if not await self.authenticate_users():
                print("❌ Authentication failed. Cannot proceed with tests.")
                return
            
            # Setup test data
            if not await self.create_test_ingredients():
                print("❌ Failed to create test ingredients. Cannot proceed.")
                return
            
            if not await self.create_test_inventory_records():
                print("❌ Failed to create test inventory records. Cannot proceed.")
                return
            
            # Run tests
            await self.test_inventory_dependencies_endpoint()
            await self.test_delete_endpoint_with_ingredient_preservation()
            await self.test_rbac_enforcement()
            await self.test_bulk_delete_scenario()
            await self.test_non_existent_inventory_delete()
            
            # Cleanup
            await self.cleanup_test_data()
            
        except Exception as e:
            print(f"❌ Test execution error: {str(e)}")
            self.results["errors"].append(f"Test execution error: {str(e)}")
        
        finally:
            await self.cleanup_session()
        
        # Print results
        self.print_results()

    def print_results(self):
        """Print test results summary"""
        print("\n" + "=" * 60)
        print("🧪 P2 BATCH 5: INVENTORY BULK DELETE BACKEND TEST RESULTS")
        print("=" * 60)
        
        total = self.results["total_tests"]
        passed = self.results["passed"]
        failed = self.results["failed"]
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"📊 SUMMARY: {passed}/{total} tests passed ({success_rate:.1f}% success rate)")
        
        if failed > 0:
            print(f"\n❌ FAILED TESTS ({failed}):")
            for error in self.results["errors"]:
                print(f"   • {error}")
        
        if success_rate == 100:
            print("\n🎯 P2 BATCH 5 INVENTORY BULK DELETE BACKEND: 100% FUNCTIONAL ✅")
            print("All dependency checking, RBAC enforcement, and master ingredient preservation working perfectly.")
        else:
            print(f"\n⚠️  P2 BATCH 5 INVENTORY BULK DELETE BACKEND: {success_rate:.1f}% FUNCTIONAL")
            print("Some issues found that need attention.")

async def main():
    """Main test execution"""
    tester = InventoryBulkDeleteTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())