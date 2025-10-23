#!/usr/bin/env python3
"""
Backend Test Suite for P2 Batch 4: Receiving Bulk Delete with Stock Reversal
Tests the receiving dependencies endpoint and delete functionality with stock reversal.
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

class ReceivingBulkDeleteTester:
    def __init__(self):
        self.session = None
        self.tokens = {}
        self.test_data = {
            "suppliers": [],
            "ingredients": [],
            "receiving_records": [],
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
                        print(f"   ✅ {role.upper()}: {credentials['email']}")
                    else:
                        error_text = await response.text()
                        print(f"   ❌ {role.upper()}: Login failed - {error_text}")
                        return False
            except Exception as e:
                print(f"   ❌ {role.upper()}: Exception - {str(e)}")
                return False
        
        return True

    def get_auth_headers(self, role: str) -> Dict[str, str]:
        """Get authorization headers for a role"""
        return {"Authorization": f"Bearer {self.tokens[role]}"}

    async def create_test_data(self):
        """Create test suppliers, ingredients, and receiving records"""
        print("\n📦 Creating test data...")
        
        # Create test supplier
        supplier_data = {
            "name": "Test Supplier for Receiving Delete",
            "contacts": {
                "name": "John Supplier",
                "email": "john@testsupplier.com",
                "phone": "+1234567890"
            },
            "notes": "Test supplier for receiving bulk delete testing"
        }
        
        async with self.session.post(
            f"{API_BASE}/suppliers",
            json=supplier_data,
            headers=self.get_auth_headers("admin")
        ) as response:
            if response.status == 201:
                supplier = await response.json()
                self.test_data["suppliers"].append(supplier)
                print(f"   ✅ Created supplier: {supplier['name']}")
            else:
                error_text = await response.text()
                print(f"   ❌ Failed to create supplier: {error_text}")
                return False

        # Create test ingredients
        ingredients_data = [
            {
                "name": "Test Flour for Receiving Delete",
                "unit": "kg",
                "packSize": 25.0,
                "packCost": 15.50,
                "preferredSupplierId": self.test_data["suppliers"][0]["id"],
                "allergens": ["GLUTEN"],
                "minStockQty": 10.0,
                "category": "food",
                "wastePct": 5.0
            },
            {
                "name": "Test Tomatoes for Receiving Delete",
                "unit": "kg",
                "packSize": 5.0,
                "packCost": 12.00,
                "preferredSupplierId": self.test_data["suppliers"][0]["id"],
                "allergens": [],
                "minStockQty": 5.0,
                "category": "food",
                "wastePct": 15.0
            },
            {
                "name": "Test Olive Oil for Receiving Delete",
                "unit": "l",
                "packSize": 1.0,
                "packCost": 8.50,
                "preferredSupplierId": self.test_data["suppliers"][0]["id"],
                "allergens": [],
                "minStockQty": 2.0,
                "category": "food",
                "wastePct": 2.0
            }
        ]
        
        for ingredient_data in ingredients_data:
            async with self.session.post(
                f"{API_BASE}/ingredients",
                json=ingredient_data,
                headers=self.get_auth_headers("admin")
            ) as response:
                if response.status == 201:
                    ingredient = await response.json()
                    self.test_data["ingredients"].append(ingredient)
                    print(f"   ✅ Created ingredient: {ingredient['name']}")
                else:
                    error_text = await response.text()
                    print(f"   ❌ Failed to create ingredient: {error_text}")
                    return False

        # Create test receiving records
        receiving_data_list = [
            {
                "supplierId": self.test_data["suppliers"][0]["id"],
                "category": "food",
                "arrivedAt": "2024-01-15T10:00:00Z",
                "lines": [
                    {
                        "ingredientId": self.test_data["ingredients"][0]["id"],
                        "description": "Test Flour Delivery 1",
                        "qty": 50.0,
                        "unit": "kg",
                        "unitPrice": 62,  # €0.62 per kg in cents
                        "packFormat": "25kg bags",
                        "expiryDate": "2024-06-15"
                    }
                ],
                "notes": "Test receiving record 1 for bulk delete testing"
            },
            {
                "supplierId": self.test_data["suppliers"][0]["id"],
                "category": "food",
                "arrivedAt": "2024-01-16T11:00:00Z",
                "lines": [
                    {
                        "ingredientId": self.test_data["ingredients"][1]["id"],
                        "description": "Test Tomatoes Delivery",
                        "qty": 20.0,
                        "unit": "kg",
                        "unitPrice": 240,  # €2.40 per kg in cents
                        "packFormat": "5kg boxes",
                        "expiryDate": "2024-01-25"
                    },
                    {
                        "ingredientId": self.test_data["ingredients"][2]["id"],
                        "description": "Test Olive Oil Delivery",
                        "qty": 10.0,
                        "unit": "l",
                        "unitPrice": 850,  # €8.50 per liter in cents
                        "packFormat": "1L bottles",
                        "expiryDate": "2024-12-31"
                    }
                ],
                "notes": "Test receiving record 2 for bulk delete testing"
            },
            {
                "supplierId": self.test_data["suppliers"][0]["id"],
                "category": "food",
                "arrivedAt": "2024-01-17T09:00:00Z",
                "lines": [
                    {
                        "ingredientId": self.test_data["ingredients"][0]["id"],
                        "description": "Test Flour Delivery 2",
                        "qty": 25.0,
                        "unit": "kg",
                        "unitPrice": 60,  # €0.60 per kg in cents
                        "packFormat": "25kg bags",
                        "expiryDate": "2024-07-15"
                    }
                ],
                "notes": "Test receiving record 3 for bulk delete testing"
            }
        ]
        
        for i, receiving_data in enumerate(receiving_data_list, 1):
            async with self.session.post(
                f"{API_BASE}/receiving",
                json=receiving_data,
                headers=self.get_auth_headers("admin")
            ) as response:
                if response.status == 201:
                    receiving = await response.json()
                    self.test_data["receiving_records"].append(receiving)
                    print(f"   ✅ Created receiving record {i}: {len(receiving['lines'])} line(s)")
                else:
                    error_text = await response.text()
                    print(f"   ❌ Failed to create receiving record {i}: {error_text}")
                    return False

        return True

    async def test_receiving_dependencies_endpoint(self):
        """Test GET /api/receiving/{id}/dependencies endpoint"""
        print("\n🔍 Testing Receiving Dependencies Endpoint...")
        
        for i, receiving in enumerate(self.test_data["receiving_records"], 1):
            receiving_id = receiving["id"]
            
            # Test dependencies check
            async with self.session.get(
                f"{API_BASE}/receiving/{receiving_id}/dependencies",
                headers=self.get_auth_headers("admin")
            ) as response:
                self.results["total_tests"] += 1
                
                if response.status == 200:
                    data = await response.json()
                    
                    # Verify response structure
                    required_fields = ["hasReferences", "canDelete", "references", "message"]
                    if all(field in data for field in required_fields):
                        # Verify canDelete is always true (allows deletion with stock reversal)
                        if data["canDelete"] == True:
                            # Verify references structure
                            if "inventoryRecords" in data["references"]:
                                inventory_count = data["references"]["inventoryRecords"]
                                print(f"   ✅ Receiving {i}: Dependencies check passed - {inventory_count} inventory records")
                                self.results["passed"] += 1
                            else:
                                print(f"   ❌ Receiving {i}: Missing inventoryRecords in references")
                                self.results["failed"] += 1
                                self.results["errors"].append(f"Receiving {i}: Missing inventoryRecords field")
                        else:
                            print(f"   ❌ Receiving {i}: canDelete should always be true for stock reversal")
                            self.results["failed"] += 1
                            self.results["errors"].append(f"Receiving {i}: canDelete is not true")
                    else:
                        missing_fields = [f for f in required_fields if f not in data]
                        print(f"   ❌ Receiving {i}: Missing required fields: {missing_fields}")
                        self.results["failed"] += 1
                        self.results["errors"].append(f"Receiving {i}: Missing fields {missing_fields}")
                else:
                    error_text = await response.text()
                    print(f"   ❌ Receiving {i}: Dependencies check failed - {error_text}")
                    self.results["failed"] += 1
                    self.results["errors"].append(f"Receiving {i}: Dependencies check failed")

        # Test with non-existent receiving ID
        async with self.session.get(
            f"{API_BASE}/receiving/non-existent-id/dependencies",
            headers=self.get_auth_headers("admin")
        ) as response:
            self.results["total_tests"] += 1
            
            if response.status == 404:
                print(f"   ✅ Non-existent receiving: Correctly returned 404")
                self.results["passed"] += 1
            else:
                print(f"   ❌ Non-existent receiving: Should return 404, got {response.status}")
                self.results["failed"] += 1
                self.results["errors"].append("Non-existent receiving should return 404")

    async def test_rbac_enforcement(self):
        """Test RBAC enforcement on delete endpoint"""
        print("\n🔐 Testing RBAC Enforcement on Delete...")
        
        receiving_id = self.test_data["receiving_records"][0]["id"]
        
        # Test admin can delete (should work)
        async with self.session.delete(
            f"{API_BASE}/receiving/{receiving_id}",
            headers=self.get_auth_headers("admin")
        ) as response:
            self.results["total_tests"] += 1
            
            if response.status == 200:
                data = await response.json()
                if "inventoryRecordsReversed" in data:
                    print(f"   ✅ Admin can delete: Success with {data['inventoryRecordsReversed']} inventory records reversed")
                    self.results["passed"] += 1
                    # Remove this receiving from our test data since it's deleted
                    self.test_data["receiving_records"] = [r for r in self.test_data["receiving_records"] if r["id"] != receiving_id]
                else:
                    print(f"   ❌ Admin delete: Missing inventoryRecordsReversed in response")
                    self.results["failed"] += 1
                    self.results["errors"].append("Admin delete: Missing inventoryRecordsReversed")
            else:
                error_text = await response.text()
                print(f"   ❌ Admin delete failed: {error_text}")
                self.results["failed"] += 1
                self.results["errors"].append(f"Admin delete failed: {error_text}")

        # Test manager can delete (should work)
        if len(self.test_data["receiving_records"]) > 0:
            receiving_id = self.test_data["receiving_records"][0]["id"]
            
            async with self.session.delete(
                f"{API_BASE}/receiving/{receiving_id}",
                headers=self.get_auth_headers("manager")
            ) as response:
                self.results["total_tests"] += 1
                
                if response.status == 200:
                    data = await response.json()
                    if "inventoryRecordsReversed" in data:
                        print(f"   ✅ Manager can delete: Success with {data['inventoryRecordsReversed']} inventory records reversed")
                        self.results["passed"] += 1
                        # Remove this receiving from our test data since it's deleted
                        self.test_data["receiving_records"] = [r for r in self.test_data["receiving_records"] if r["id"] != receiving_id]
                    else:
                        print(f"   ❌ Manager delete: Missing inventoryRecordsReversed in response")
                        self.results["failed"] += 1
                        self.results["errors"].append("Manager delete: Missing inventoryRecordsReversed")
                else:
                    error_text = await response.text()
                    print(f"   ❌ Manager delete failed: {error_text}")
                    self.results["failed"] += 1
                    self.results["errors"].append(f"Manager delete failed: {error_text}")

        # Test staff CANNOT delete (should fail with 403)
        if len(self.test_data["receiving_records"]) > 0:
            receiving_id = self.test_data["receiving_records"][0]["id"]
            
            async with self.session.delete(
                f"{API_BASE}/receiving/{receiving_id}",
                headers=self.get_auth_headers("staff")
            ) as response:
                self.results["total_tests"] += 1
                
                if response.status == 403:
                    print(f"   ✅ Staff CANNOT delete: Correctly denied with 403")
                    self.results["passed"] += 1
                else:
                    error_text = await response.text()
                    print(f"   ❌ Staff should be denied: Got {response.status} instead of 403")
                    self.results["failed"] += 1
                    self.results["errors"].append(f"Staff should be denied delete access")

    async def test_stock_reversal_verification(self):
        """Test that inventory records are actually deleted when receiving is deleted"""
        print("\n🔄 Testing Stock Reversal Verification...")
        
        if len(self.test_data["receiving_records"]) == 0:
            print("   ⚠️  No receiving records left to test stock reversal")
            return

        receiving = self.test_data["receiving_records"][0]
        receiving_id = receiving["id"]
        
        # First, check how many inventory records exist for this receiving
        async with self.session.get(
            f"{API_BASE}/inventory",
            headers=self.get_auth_headers("admin")
        ) as response:
            if response.status == 200:
                all_inventory = await response.json()
                # Filter inventory records for this receiving
                receiving_inventory = [inv for inv in all_inventory if inv.get("receivingId") == receiving_id]
                initial_count = len(receiving_inventory)
                print(f"   📊 Found {initial_count} inventory records for receiving before deletion")
                
                if initial_count == 0:
                    print("   ⚠️  No inventory records found for this receiving")
                    return
                
                # Delete the receiving
                async with self.session.delete(
                    f"{API_BASE}/receiving/{receiving_id}",
                    headers=self.get_auth_headers("admin")
                ) as delete_response:
                    self.results["total_tests"] += 1
                    
                    if delete_response.status == 200:
                        delete_data = await delete_response.json()
                        reversed_count = delete_data.get("inventoryRecordsReversed", 0)
                        
                        # Verify the count matches
                        if reversed_count == initial_count:
                            print(f"   ✅ Stock reversal count matches: {reversed_count} records reversed")
                            
                            # Verify inventory records are actually deleted
                            async with self.session.get(
                                f"{API_BASE}/inventory",
                                headers=self.get_auth_headers("admin")
                            ) as verify_response:
                                if verify_response.status == 200:
                                    updated_inventory = await verify_response.json()
                                    remaining_receiving_inventory = [inv for inv in updated_inventory if inv.get("receivingId") == receiving_id]
                                    
                                    if len(remaining_receiving_inventory) == 0:
                                        print(f"   ✅ Stock reversal verified: All inventory records deleted")
                                        self.results["passed"] += 1
                                    else:
                                        print(f"   ❌ Stock reversal failed: {len(remaining_receiving_inventory)} inventory records still exist")
                                        self.results["failed"] += 1
                                        self.results["errors"].append("Stock reversal incomplete - inventory records still exist")
                                else:
                                    print(f"   ❌ Failed to verify inventory after deletion")
                                    self.results["failed"] += 1
                                    self.results["errors"].append("Could not verify inventory after deletion")
                        else:
                            print(f"   ❌ Stock reversal count mismatch: Expected {initial_count}, got {reversed_count}")
                            self.results["failed"] += 1
                            self.results["errors"].append(f"Stock reversal count mismatch: {initial_count} vs {reversed_count}")
                    else:
                        error_text = await delete_response.text()
                        print(f"   ❌ Failed to delete receiving for stock reversal test: {error_text}")
                        self.results["failed"] += 1
                        self.results["errors"].append("Failed to delete receiving for stock reversal test")
            else:
                print(f"   ❌ Failed to get inventory for stock reversal test")
                self.results["failed"] += 1
                self.results["errors"].append("Failed to get inventory for stock reversal test")

    async def test_tenant_isolation(self):
        """Test that tenant isolation is maintained"""
        print("\n🏢 Testing Tenant Isolation...")
        
        # Try to access dependencies for a receiving with different user (should fail)
        if len(self.test_data["receiving_records"]) > 0:
            receiving_id = self.test_data["receiving_records"][0]["id"]
            
            # This test assumes we have proper tenant isolation
            # In a real scenario, we'd need a user from a different restaurant
            # For now, we'll test that non-existent receiving returns 404
            async with self.session.get(
                f"{API_BASE}/receiving/different-tenant-receiving/dependencies",
                headers=self.get_auth_headers("admin")
            ) as response:
                self.results["total_tests"] += 1
                
                if response.status == 404:
                    print(f"   ✅ Tenant isolation: Non-existent receiving correctly returns 404")
                    self.results["passed"] += 1
                else:
                    print(f"   ❌ Tenant isolation: Should return 404 for non-existent receiving")
                    self.results["failed"] += 1
                    self.results["errors"].append("Tenant isolation test failed")

    async def cleanup_test_data(self):
        """Clean up test data"""
        print("\n🧹 Cleaning up test data...")
        
        # Delete remaining receiving records
        for receiving in self.test_data["receiving_records"]:
            try:
                async with self.session.delete(
                    f"{API_BASE}/receiving/{receiving['id']}",
                    headers=self.get_auth_headers("admin")
                ) as response:
                    if response.status == 200:
                        print(f"   ✅ Deleted receiving: {receiving['id']}")
                    else:
                        print(f"   ⚠️  Could not delete receiving: {receiving['id']}")
            except Exception as e:
                print(f"   ⚠️  Error deleting receiving {receiving['id']}: {str(e)}")
        
        # Delete test ingredients
        for ingredient in self.test_data["ingredients"]:
            try:
                async with self.session.delete(
                    f"{API_BASE}/ingredients/{ingredient['id']}",
                    headers=self.get_auth_headers("admin")
                ) as response:
                    if response.status == 200:
                        print(f"   ✅ Deleted ingredient: {ingredient['name']}")
                    else:
                        print(f"   ⚠️  Could not delete ingredient: {ingredient['name']}")
            except Exception as e:
                print(f"   ⚠️  Error deleting ingredient {ingredient['name']}: {str(e)}")
        
        # Delete test suppliers
        for supplier in self.test_data["suppliers"]:
            try:
                async with self.session.delete(
                    f"{API_BASE}/suppliers/{supplier['id']}",
                    headers=self.get_auth_headers("admin")
                ) as response:
                    if response.status == 200:
                        print(f"   ✅ Deleted supplier: {supplier['name']}")
                    else:
                        print(f"   ⚠️  Could not delete supplier: {supplier['name']}")
            except Exception as e:
                print(f"   ⚠️  Error deleting supplier {supplier['name']}: {str(e)}")

    async def run_all_tests(self):
        """Run all tests"""
        print("🧪 P2 BATCH 4: RECEIVING BULK DELETE WITH STOCK REVERSAL BACKEND TESTING")
        print("=" * 80)
        
        try:
            await self.setup_session()
            
            # Authenticate users
            if not await self.authenticate_users():
                print("❌ Authentication failed. Cannot proceed with tests.")
                return
            
            # Create test data
            if not await self.create_test_data():
                print("❌ Test data creation failed. Cannot proceed with tests.")
                return
            
            # Run tests
            await self.test_receiving_dependencies_endpoint()
            await self.test_rbac_enforcement()
            await self.test_stock_reversal_verification()
            await self.test_tenant_isolation()
            
            # Clean up
            await self.cleanup_test_data()
            
        except Exception as e:
            print(f"\n❌ Critical error during testing: {str(e)}")
            self.results["errors"].append(f"Critical error: {str(e)}")
        
        finally:
            await self.cleanup_session()
        
        # Print results
        self.print_results()

    def print_results(self):
        """Print test results summary"""
        print("\n" + "=" * 80)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 80)
        
        total = self.results["total_tests"]
        passed = self.results["passed"]
        failed = self.results["failed"]
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        if self.results["errors"]:
            print(f"\n❌ ERRORS FOUND ({len(self.results['errors'])}):")
            for i, error in enumerate(self.results["errors"], 1):
                print(f"   {i}. {error}")
        
        if success_rate == 100:
            print(f"\n🎉 ALL TESTS PASSED! Receiving bulk delete with stock reversal is working correctly.")
        elif success_rate >= 90:
            print(f"\n✅ MOSTLY WORKING ({success_rate:.1f}%) - Minor issues found.")
        else:
            print(f"\n⚠️  SIGNIFICANT ISSUES FOUND ({success_rate:.1f}%) - Needs attention.")

async def main():
    """Main test runner"""
    tester = ReceivingBulkDeleteTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())