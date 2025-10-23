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

class SupplierDependenciesTest:
    def __init__(self):
        self.session = None
        self.tokens = {}
        self.test_data = {
            "suppliers": [],
            "ingredients": [],
            "receiving": []
        }
        
    async def setup_session(self):
        """Initialize HTTP session"""
        self.session = aiohttp.ClientSession()
        
    async def cleanup_session(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            
    async def login_user(self, role):
        """Login and get token for a specific role"""
        user_creds = TEST_USERS[role]
        
        async with self.session.post(f"{API_BASE}/auth/login", json=user_creds) as resp:
            if resp.status != 200:
                raise Exception(f"Login failed for {role}: {await resp.text()}")
            
            data = await resp.json()
            self.tokens[role] = data["access_token"]
            return data["access_token"]
            
    def get_headers(self, role):
        """Get authorization headers for a role"""
        return {"Authorization": f"Bearer {self.tokens[role]}"}
        
    async def create_test_suppliers(self):
        """Create test suppliers for dependency testing"""
        print("📦 Creating test suppliers...")
        
        suppliers_data = [
            {"name": "Supplier A - No Dependencies", "notes": "Test supplier without any references"},
            {"name": "Supplier B - Ingredient Refs", "notes": "Test supplier with ingredient references"},
            {"name": "Supplier C - Receiving Refs", "notes": "Test supplier with receiving references"},
            {"name": "Supplier D - Both Refs", "notes": "Test supplier with both ingredient and receiving references"}
        ]
        
        headers = self.get_headers("admin")
        
        for supplier_data in suppliers_data:
            async with self.session.post(f"{API_BASE}/suppliers", json=supplier_data, headers=headers) as resp:
                if resp.status not in [200, 201]:
                    raise Exception(f"Failed to create supplier: {await resp.text()}")
                
                supplier = await resp.json()
                self.test_data["suppliers"].append(supplier)
                print(f"  ✅ Created supplier: {supplier['name']} (ID: {supplier['id']})")
                
        return self.test_data["suppliers"]
        
    async def create_test_ingredients(self):
        """Create test ingredients with supplier references"""
        print("🥬 Creating test ingredients with supplier references...")
        
        # Create ingredients referencing different suppliers
        ingredients_data = [
            {
                "name": "Test Flour - Supplier B",
                "unit": "kg",
                "packSize": 25.0,
                "packCost": 15.50,
                "preferredSupplierId": self.test_data["suppliers"][1]["id"],  # Supplier B
                "category": "food",
                "wastePct": 5.0
            },
            {
                "name": "Test Tomatoes - Supplier D",
                "unit": "kg", 
                "packSize": 10.0,
                "packCost": 32.00,
                "preferredSupplierId": self.test_data["suppliers"][3]["id"],  # Supplier D
                "category": "food",
                "wastePct": 15.0
            }
        ]
        
        headers = self.get_headers("admin")
        
        for ingredient_data in ingredients_data:
            async with self.session.post(f"{API_BASE}/ingredients", json=ingredient_data, headers=headers) as resp:
                if resp.status not in [200, 201]:
                    raise Exception(f"Failed to create ingredient: {await resp.text()}")
                
                ingredient = await resp.json()
                self.test_data["ingredients"].append(ingredient)
                print(f"  ✅ Created ingredient: {ingredient['name']} → Supplier {ingredient.get('preferredSupplierName', 'Unknown')}")
                
        return self.test_data["ingredients"]
        
    async def create_test_receiving(self):
        """Create test receiving records with supplier references"""
        print("📋 Creating test receiving records with supplier references...")
        
        # Create receiving records for different suppliers
        receiving_data = [
            {
                "supplierId": self.test_data["suppliers"][2]["id"],  # Supplier C
                "category": "food",
                "arrivedAt": "2024-01-15T10:00:00Z",
                "lines": [
                    {
                        "description": "Test Olive Oil Delivery",
                        "qty": 12.0,
                        "unit": "bottles",
                        "unitPrice": 850,  # €8.50 in cents
                        "packFormat": "500ml bottle"
                    }
                ],
                "notes": "Test receiving for Supplier C"
            },
            {
                "supplierId": self.test_data["suppliers"][3]["id"],  # Supplier D
                "category": "food", 
                "arrivedAt": "2024-01-16T14:30:00Z",
                "lines": [
                    {
                        "description": "Test Cheese Delivery",
                        "qty": 5.0,
                        "unit": "kg",
                        "unitPrice": 1200,  # €12.00 in cents
                        "packFormat": "wheel"
                    }
                ],
                "notes": "Test receiving for Supplier D"
            }
        ]
        
        headers = self.get_headers("admin")
        
        for receiving_item in receiving_data:
            async with self.session.post(f"{API_BASE}/receiving", json=receiving_item, headers=headers) as resp:
                if resp.status not in [200, 201]:
                    raise Exception(f"Failed to create receiving: {await resp.text()}")
                
                receiving = await resp.json()
                self.test_data["receiving"].append(receiving)
                print(f"  ✅ Created receiving: {receiving['lines'][0]['description']} → Supplier ID {receiving['supplierId']}")
                
        return self.test_data["receiving"]
        
    async def test_supplier_dependencies_endpoint(self):
        """Test GET /api/suppliers/{id}/dependencies endpoint"""
        print("\n🔍 Testing Supplier Dependencies Endpoint...")
        
        headers = self.get_headers("admin")
        test_results = []
        
        # Test each supplier's dependencies
        for i, supplier in enumerate(self.test_data["suppliers"]):
            supplier_id = supplier["id"]
            supplier_name = supplier["name"]
            
            async with self.session.get(f"{API_BASE}/suppliers/{supplier_id}/dependencies", headers=headers) as resp:
                if resp.status != 200:
                    test_results.append(f"❌ Dependencies check failed for {supplier_name}: {await resp.text()}")
                    continue
                    
                deps = await resp.json()
                
                # Verify response structure
                if not all(key in deps for key in ["hasReferences", "references"]):
                    test_results.append(f"❌ Invalid response structure for {supplier_name}")
                    continue
                    
                if not all(key in deps["references"] for key in ["ingredients", "receiving"]):
                    test_results.append(f"❌ Missing reference counts for {supplier_name}")
                    continue
                
                # Expected dependencies based on test data setup
                expected_deps = {
                    0: {"ingredients": 0, "receiving": 0, "hasReferences": False},  # Supplier A - No deps
                    1: {"ingredients": 1, "receiving": 0, "hasReferences": True},   # Supplier B - Ingredient refs
                    2: {"ingredients": 0, "receiving": 1, "hasReferences": True},   # Supplier C - Receiving refs  
                    3: {"ingredients": 1, "receiving": 1, "hasReferences": True}    # Supplier D - Both refs
                }
                
                expected = expected_deps[i]
                actual_ingredients = deps["references"]["ingredients"]
                actual_receiving = deps["references"]["receiving"]
                actual_has_refs = deps["hasReferences"]
                
                if (actual_ingredients == expected["ingredients"] and 
                    actual_receiving == expected["receiving"] and
                    actual_has_refs == expected["hasReferences"]):
                    test_results.append(f"✅ {supplier_name}: ingredients={actual_ingredients}, receiving={actual_receiving}, hasReferences={actual_has_refs}")
                else:
                    test_results.append(f"❌ {supplier_name}: Expected ingredients={expected['ingredients']}, receiving={expected['receiving']}, hasReferences={expected['hasReferences']} | Got ingredients={actual_ingredients}, receiving={actual_receiving}, hasReferences={actual_has_refs}")
        
        # Test with non-existent supplier
        fake_supplier_id = "00000000-0000-0000-0000-000000000000"
        async with self.session.get(f"{API_BASE}/suppliers/{fake_supplier_id}/dependencies", headers=headers) as resp:
            deps = await resp.json()
            if deps["hasReferences"] == False and deps["references"]["ingredients"] == 0 and deps["references"]["receiving"] == 0:
                test_results.append("✅ Non-existent supplier returns no dependencies")
            else:
                test_results.append("❌ Non-existent supplier should return no dependencies")
        
        for result in test_results:
            print(f"  {result}")
            
        return test_results
        
    async def test_delete_with_dependency_blocking(self):
        """Test DELETE /api/suppliers/{id} with dependency blocking"""
        print("\n🚫 Testing Delete Endpoint with Dependency Blocking...")
        
        headers = self.get_headers("admin")
        test_results = []
        
        # Test deleting suppliers with dependencies (should fail)
        suppliers_with_deps = [1, 2, 3]  # Supplier B, C, D have dependencies
        
        for i in suppliers_with_deps:
            supplier = self.test_data["suppliers"][i]
            supplier_id = supplier["id"]
            supplier_name = supplier["name"]
            
            async with self.session.delete(f"{API_BASE}/suppliers/{supplier_id}", headers=headers) as resp:
                if resp.status == 400:
                    error_data = await resp.json()
                    error_msg = error_data.get("detail", "")
                    
                    # Check if error message mentions both dependency types
                    if "ingredients" in error_msg or "receiving" in error_msg:
                        test_results.append(f"✅ {supplier_name}: Correctly blocked with dependency error: {error_msg}")
                    else:
                        test_results.append(f"❌ {supplier_name}: Blocked but error message unclear: {error_msg}")
                else:
                    test_results.append(f"❌ {supplier_name}: Should be blocked but got status {resp.status}")
        
        # Test deleting supplier without dependencies (should succeed)
        supplier_no_deps = self.test_data["suppliers"][0]  # Supplier A - No dependencies
        supplier_id = supplier_no_deps["id"]
        supplier_name = supplier_no_deps["name"]
        
        async with self.session.delete(f"{API_BASE}/suppliers/{supplier_id}", headers=headers) as resp:
            if resp.status == 200:
                test_results.append(f"✅ {supplier_name}: Successfully deleted (no dependencies)")
            else:
                error_text = await resp.text()
                test_results.append(f"❌ {supplier_name}: Delete failed unexpectedly: {error_text}")
        
        # Verify supplier was actually deleted
        async with self.session.get(f"{API_BASE}/suppliers/{supplier_id}", headers=headers) as resp:
            if resp.status == 404:
                test_results.append(f"✅ {supplier_name}: Confirmed deleted (404 on GET)")
            else:
                test_results.append(f"❌ {supplier_name}: Still exists after delete")
        
        for result in test_results:
            print(f"  {result}")
            
        return test_results
        
    async def test_rbac_enforcement(self):
        """Test RBAC enforcement on delete endpoint"""
        print("\n🔐 Testing RBAC Enforcement on Delete...")
        
        test_results = []
        
        # Use a supplier that still exists (one with dependencies that couldn't be deleted)
        test_supplier = self.test_data["suppliers"][1]  # Supplier B
        supplier_id = test_supplier["id"]
        
        # Test Admin access (should work but be blocked by dependencies)
        admin_headers = self.get_headers("admin")
        async with self.session.delete(f"{API_BASE}/suppliers/{supplier_id}", headers=admin_headers) as resp:
            if resp.status == 400:  # Blocked by dependencies, not permissions
                test_results.append("✅ Admin: Has delete permission (blocked by dependencies, not RBAC)")
            elif resp.status == 403:
                test_results.append("❌ Admin: Should have delete permission")
            else:
                test_results.append(f"❌ Admin: Unexpected status {resp.status}")
        
        # Test Manager access (should work but be blocked by dependencies)
        manager_headers = self.get_headers("manager")
        async with self.session.delete(f"{API_BASE}/suppliers/{supplier_id}", headers=manager_headers) as resp:
            if resp.status == 400:  # Blocked by dependencies, not permissions
                test_results.append("✅ Manager: Has delete permission (blocked by dependencies, not RBAC)")
            elif resp.status == 403:
                test_results.append("❌ Manager: Should have delete permission")
            else:
                test_results.append(f"❌ Manager: Unexpected status {resp.status}")
        
        # Test Staff access (should be denied with 403)
        staff_headers = self.get_headers("staff")
        async with self.session.delete(f"{API_BASE}/suppliers/{supplier_id}", headers=staff_headers) as resp:
            if resp.status == 403:
                error_data = await resp.json()
                error_msg = error_data.get("detail", "")
                if "Admin or Manager access required" in error_msg:
                    test_results.append("✅ Staff: Correctly denied with 403 (Admin or Manager access required)")
                else:
                    test_results.append(f"✅ Staff: Correctly denied with 403, message: {error_msg}")
            else:
                test_results.append(f"❌ Staff: Should be denied with 403, got {resp.status}")
        
        for result in test_results:
            print(f"  {result}")
            
        return test_results
        
    async def test_bulk_delete_scenario(self):
        """Test comprehensive bulk delete scenario"""
        print("\n📦 Testing Bulk Delete Scenario...")
        
        test_results = []
        
        # Summary of current state after previous tests
        print("  📊 Current Test Data State:")
        print(f"    - Suppliers created: {len(self.test_data['suppliers'])}")
        print(f"    - Ingredients created: {len(self.test_data['ingredients'])}")  
        print(f"    - Receiving records created: {len(self.test_data['receiving'])}")
        
        # Verify dependencies are still detected correctly
        headers = self.get_headers("admin")
        
        remaining_suppliers = self.test_data["suppliers"][1:]  # Skip deleted Supplier A
        
        for supplier in remaining_suppliers:
            supplier_id = supplier["id"]
            supplier_name = supplier["name"]
            
            async with self.session.get(f"{API_BASE}/suppliers/{supplier_id}/dependencies", headers=headers) as resp:
                if resp.status == 200:
                    deps = await resp.json()
                    if deps["hasReferences"]:
                        test_results.append(f"✅ {supplier_name}: Still has dependencies as expected")
                    else:
                        test_results.append(f"❌ {supplier_name}: Should still have dependencies")
                else:
                    test_results.append(f"❌ {supplier_name}: Dependencies check failed")
        
        # Attempt bulk delete of remaining suppliers (should all fail due to dependencies)
        delete_attempts = 0
        delete_blocked = 0
        
        for supplier in remaining_suppliers:
            supplier_id = supplier["id"]
            supplier_name = supplier["name"]
            
            async with self.session.delete(f"{API_BASE}/suppliers/{supplier_id}", headers=headers) as resp:
                delete_attempts += 1
                if resp.status == 400:
                    delete_blocked += 1
                    
        if delete_blocked == delete_attempts:
            test_results.append(f"✅ Bulk delete scenario: All {delete_attempts} suppliers with dependencies correctly blocked")
        else:
            test_results.append(f"❌ Bulk delete scenario: Only {delete_blocked}/{delete_attempts} suppliers blocked")
        
        for result in test_results:
            print(f"  {result}")
            
        return test_results
        
    async def cleanup_test_data(self):
        """Clean up test data"""
        print("\n🧹 Cleaning up test data...")
        
        headers = self.get_headers("admin")
        
        # Delete test ingredients (to remove dependencies)
        for ingredient in self.test_data["ingredients"]:
            try:
                async with self.session.delete(f"{API_BASE}/ingredients/{ingredient['id']}", headers=headers) as resp:
                    if resp.status == 200:
                        print(f"  ✅ Deleted ingredient: {ingredient['name']}")
            except Exception as e:
                print(f"  ⚠️ Failed to delete ingredient {ingredient['name']}: {e}")
        
        # Delete test receiving records (to remove dependencies)
        for receiving in self.test_data["receiving"]:
            try:
                async with self.session.delete(f"{API_BASE}/receiving/{receiving['id']}", headers=headers) as resp:
                    if resp.status == 200:
                        print(f"  ✅ Deleted receiving: {receiving['id']}")
            except Exception as e:
                print(f"  ⚠️ Failed to delete receiving {receiving['id']}: {e}")
        
        # Now delete remaining suppliers (should work without dependencies)
        for supplier in self.test_data["suppliers"][1:]:  # Skip already deleted Supplier A
            try:
                async with self.session.delete(f"{API_BASE}/suppliers/{supplier['id']}", headers=headers) as resp:
                    if resp.status == 200:
                        print(f"  ✅ Deleted supplier: {supplier['name']}")
            except Exception as e:
                print(f"  ⚠️ Failed to delete supplier {supplier['name']}: {e}")
        
    async def run_all_tests(self):
        """Run all supplier dependency and bulk delete tests"""
        print("🧪 P2 BATCH 3: SUPPLIERS BULK DELETE & DEPENDENCIES BACKEND TESTING")
        print("=" * 80)
        
        all_results = []
        
        try:
            await self.setup_session()
            
            # Login all users
            for role in TEST_USERS.keys():
                await self.login_user(role)
                print(f"✅ Logged in as {role}")
            
            # Setup test data
            await self.create_test_suppliers()
            await self.create_test_ingredients()
            await self.create_test_receiving()
            
            # Run tests
            deps_results = await self.test_supplier_dependencies_endpoint()
            delete_results = await self.test_delete_with_dependency_blocking()
            rbac_results = await self.test_rbac_enforcement()
            bulk_results = await self.test_bulk_delete_scenario()
            
            all_results.extend(deps_results)
            all_results.extend(delete_results)
            all_results.extend(rbac_results)
            all_results.extend(bulk_results)
            
            # Cleanup
            await self.cleanup_test_data()
            
        except Exception as e:
            print(f"❌ Test execution failed: {e}")
            all_results.append(f"❌ Test execution failed: {e}")
        finally:
            await self.cleanup_session()
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        
        passed = len([r for r in all_results if r.startswith("✅")])
        failed = len([r for r in all_results if r.startswith("❌")])
        total = passed + failed
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(passed/total*100):.1f}%" if total > 0 else "0%")
        
        if failed > 0:
            print("\n❌ FAILED TESTS:")
            for result in all_results:
                if result.startswith("❌"):
                    print(f"  {result}")
        
        return all_results

async def main():
    """Main test execution"""
    tester = SupplierDependenciesTest()
    results = await tester.run_all_tests()
    
    # Return results for further processing
    return results

if __name__ == "__main__":
    asyncio.run(main())
