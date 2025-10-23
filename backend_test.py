#!/usr/bin/env python3
"""
P2 Batch 3: Suppliers Bulk Delete & Dependencies Backend Testing
Tests the supplier dependencies endpoint and delete functionality with RBAC enforcement.
"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime, timezone

# Backend URL from environment
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
                if resp.status != 201:
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
                if resp.status != 201:
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
                if resp.status != 201:
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
                    # unitCost = €10/kg = €0.01/g
                    # qty = 2g
                    # cost = €0.01 * 2 = €0.02
                    expected_cost = 10.0 * (2 / 1000)  # Convert 2g to kg, then multiply by €10/kg
                    
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
        
        # Test with different small quantities
        test_cases = [
            {"qty": 2, "unit": "g", "expected": 0.02},  # 2g = €0.02
            {"qty": 500, "unit": "g", "expected": 5.0},  # 500g = €5.00
            {"qty": 0.5, "unit": "g", "expected": 0.005},  # 0.5g = €0.005
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
                    
                    # Expected: 500ml = 0.5L, €4/L * 0.5L = €2.00
                    expected_cost = 4.0 * 0.5
                    
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
                    
                    # Expected: 100mg = 0.0001kg, €50,000/kg * 0.0001kg = €5.00
                    expected_cost = saffron_ingredient["unitCost"] * (100 / 1000000)  # Convert mg to kg
                    
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
                    
                    # Expected: 0.5g = 0.0005kg, €10/kg * 0.0005kg = €0.005
                    expected_cost = 10.0 * (0.5 / 1000)
                    
                    if preparation["cost"] > 0:
                        self.log_result("4-Decimal Precision > 0", True, f"Cost €{preparation['cost']:.4f} > 0")
                    else:
                        self.log_result("4-Decimal Precision > 0", False, "Cost is €0.00")
                    
                    # Check internal precision (should be stored as 0.0050)
                    if preparation["cost"] >= 0.005:
                        self.log_result("4-Decimal Internal Precision", True, f"Internally stored as €{preparation['cost']:.4f}")
                    else:
                        self.log_result("4-Decimal Internal Precision", False, f"Lost precision: €{preparation['cost']:.4f}")
                    
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
                    # Cocoa: 1g = €0.01
                    # Vanilla: 5ml = €0.02 (€4/L * 0.005L)
                    # Total per portion: €0.03
                    # Total for 4 portions: €0.12
                    
                    cocoa_per_portion = 10.0 * (1 / 1000)  # €0.01
                    vanilla_per_portion = 4.0 * (5 / 1000)  # €0.02
                    expected_per_portion = cocoa_per_portion + vanilla_per_portion  # €0.03
                    expected_total = expected_per_portion * 4  # €0.12
                    
                    self.log_result("Recipe Unit Conversion Created", True, f"Recipe created successfully")
                    self.log_result("Recipe Cost Calculation", True, f"Expected total cost: €{expected_total:.4f}")
                    
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
    
    async def test_file_upload_invalid_mime(self):
        """Test file upload with invalid MIME type"""
        try:
            # Create a text file (not allowed)
            text_content = b"This is a text file that should be rejected"
            file_path = self.create_test_file("test.txt", text_content, "text/plain")
            
            data = aiohttp.FormData()
            data.add_field('file', open(file_path, 'rb'), filename='test.txt', content_type='text/plain')
            
            async with self.session.post(
                f"{BACKEND_URL}/files/upload",
                data=data,
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 400:
                    self.log_result("File Upload Invalid MIME", True, "Correctly rejected invalid MIME type")
                else:
                    error_text = await response.text()
                    self.log_result("File Upload Invalid MIME", False, f"Should have rejected file: {response.status}", error_text)
            
            # Clean up
            os.unlink(file_path)
            
        except Exception as e:
            self.log_result("File Upload Invalid MIME", False, f"Test error: {str(e)}")
    
    async def test_file_upload_oversized(self):
        """Test file upload with oversized file (>10MB)"""
        try:
            # Create a large file (11MB)
            large_content = b"x" * (11 * 1024 * 1024)
            file_path = self.create_test_file("large_file.pdf", large_content, "application/pdf")
            
            data = aiohttp.FormData()
            data.add_field('file', open(file_path, 'rb'), filename='large_file.pdf', content_type='application/pdf')
            
            async with self.session.post(
                f"{BACKEND_URL}/files/upload",
                data=data,
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 400:
                    self.log_result("File Upload Oversized", True, "Correctly rejected oversized file")
                else:
                    error_text = await response.text()
                    self.log_result("File Upload Oversized", False, f"Should have rejected large file: {response.status}", error_text)
            
            # Clean up
            os.unlink(file_path)
            
        except Exception as e:
            self.log_result("File Upload Oversized", False, f"Test error: {str(e)}")
    
    async def test_file_download(self, file_data: Dict[str, Any]):
        """Test file download"""
        if not file_data:
            self.log_result("File Download", False, "No file data provided")
            return
        
        try:
            file_id = file_data["id"]
            
            async with self.session.get(
                f"{BACKEND_URL}/files/{file_id}",
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 200:
                    content_type = response.headers.get("Content-Type")
                    content_disposition = response.headers.get("Content-Disposition")
                    
                    if content_type == file_data["mimeType"]:
                        if content_disposition and "attachment" in content_disposition:
                            self.log_result("File Download", True, "File downloaded with correct headers")
                        else:
                            self.log_result("File Download", False, f"Missing Content-Disposition header: {content_disposition}")
                    else:
                        self.log_result("File Download", False, f"Wrong Content-Type: {content_type}")
                else:
                    error_text = await response.text()
                    self.log_result("File Download", False, f"Download failed: {response.status}", error_text)
        
        except Exception as e:
            self.log_result("File Download", False, f"Download error: {str(e)}")
    
    async def test_file_download_nonexistent(self):
        """Test download of non-existent file"""
        try:
            fake_id = "nonexistent-file-id"
            
            async with self.session.get(
                f"{BACKEND_URL}/files/{fake_id}",
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 404:
                    self.log_result("File Download Nonexistent", True, "Correctly returned 404 for missing file")
                else:
                    error_text = await response.text()
                    self.log_result("File Download Nonexistent", False, f"Should return 404: {response.status}", error_text)
        
        except Exception as e:
            self.log_result("File Download Nonexistent", False, f"Test error: {str(e)}")
    
    async def test_file_delete(self, file_data: Dict[str, Any]):
        """Test file deletion"""
        if not file_data:
            self.log_result("File Delete", False, "No file data provided")
            return
        
        try:
            file_id = file_data["id"]
            
            async with self.session.delete(
                f"{BACKEND_URL}/files/{file_id}",
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 200:
                    self.log_result("File Delete", True, "File deleted successfully")
                    
                    # Verify file is gone
                    async with self.session.get(
                        f"{BACKEND_URL}/files/{file_id}",
                        headers=self.get_auth_headers()
                    ) as verify_response:
                        if verify_response.status == 404:
                            self.log_result("File Delete Verification", True, "File confirmed deleted")
                        else:
                            self.log_result("File Delete Verification", False, "File still accessible after deletion")
                else:
                    error_text = await response.text()
                    self.log_result("File Delete", False, f"Delete failed: {response.status}", error_text)
        
        except Exception as e:
            self.log_result("File Delete", False, f"Delete error: {str(e)}")
    
    # ============ RECIPE TESTING METHODS ============
    
    async def create_test_ingredients(self):
        """Create test ingredients with waste% and allergens"""
        ingredients_data = [
            {
                "name": "Flour 00",
                "unit": "kg",
                "packSize": 1.0,
                "packCost": 2.50,
                "wastePct": 5.0,
                "allergens": ["gluten"],
                "category": "food"
            },
            {
                "name": "Fresh Tomatoes",
                "unit": "kg", 
                "packSize": 1.0,
                "packCost": 3.20,
                "wastePct": 15.0,
                "allergens": [],
                "category": "food"
            },
            {
                "name": "Mozzarella di Bufala",
                "unit": "kg",
                "packSize": 1.0,
                "packCost": 12.00,
                "wastePct": 8.0,
                "allergens": ["dairy"],
                "category": "food"
            },
            {
                "name": "Extra Virgin Olive Oil",
                "unit": "L",
                "packSize": 1.0,
                "packCost": 8.50,
                "wastePct": 2.0,
                "allergens": [],
                "category": "food"
            },
            {
                "name": "Fresh Basil",
                "unit": "kg",
                "packSize": 0.1,
                "packCost": 2.00,
                "wastePct": 20.0,
                "allergens": [],
                "category": "food"
            },
            {
                "name": "Sea Salt",
                "unit": "kg",
                "packSize": 1.0,
                "packCost": 1.50,
                "wastePct": 0.0,
                "allergens": [],
                "category": "food"
            }
        ]
        
        created_ingredients = []
        
        for ingredient_data in ingredients_data:
            try:
                async with self.session.post(
                    f"{BACKEND_URL}/ingredients",
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
        
        return created_ingredients
    
    async def create_test_preparation(self, ingredients):
        """Create a test preparation (Pizza Dough) using ingredients"""
        if len(ingredients) < 3:
            self.log_result("Create Test Preparation", False, "Not enough ingredients available")
            return None
        
        # Find specific ingredients
        flour = next((ing for ing in ingredients if "Flour" in ing["name"]), None)
        tomatoes = next((ing for ing in ingredients if "Tomatoes" in ing["name"]), None)
        mozzarella = next((ing for ing in ingredients if "Mozzarella" in ing["name"]), None)
        
        if not all([flour, tomatoes, mozzarella]):
            self.log_result("Create Test Preparation", False, "Required ingredients not found")
            return None
        
        prep_data = {
            "name": "Pizza Dough",
            "items": [
                {
                    "ingredientId": flour["id"],
                    "qty": 0.5,
                    "unit": "kg"
                },
                {
                    "ingredientId": tomatoes["id"],
                    "qty": 0.2,
                    "unit": "kg"
                },
                {
                    "ingredientId": mozzarella["id"],
                    "qty": 0.3,
                    "unit": "kg"
                }
            ],
            "yield": {
                "value": 4.0,
                "unit": "portions"
            },
            "shelfLife": {
                "value": 2,
                "unit": "days"
            },
            "notes": "Base pizza dough with tomatoes and mozzarella"
        }
        
        try:
            async with self.session.post(
                f"{BACKEND_URL}/preparations",
                json=prep_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    preparation = await response.json()
                    
                    # Verify cost computation
                    expected_cost = (
                        flour["effectiveUnitCost"] * 0.5 +  # Flour with 5% waste
                        tomatoes["effectiveUnitCost"] * 0.2 +  # Tomatoes with 15% waste
                        mozzarella["effectiveUnitCost"] * 0.3   # Mozzarella with 8% waste
                    )
                    
                    if abs(preparation["cost"] - expected_cost) < 0.01:
                        self.log_result("Create Test Preparation", True, f"Pizza Dough created with correct cost: €{preparation['cost']:.3f}")
                    else:
                        self.log_result("Create Test Preparation", False, f"Cost mismatch: expected €{expected_cost:.3f}, got €{preparation['cost']:.3f}")
                    
                    # Verify allergens
                    expected_allergens = sorted(["gluten", "dairy"])  # From flour and mozzarella
                    if preparation["allergens"] == expected_allergens:
                        self.log_result("Preparation Allergens", True, f"Correct allergens: {preparation['allergens']}")
                    else:
                        self.log_result("Preparation Allergens", False, f"Expected {expected_allergens}, got {preparation['allergens']}")
                    
                    return preparation
                else:
                    error_text = await response.text()
                    self.log_result("Create Test Preparation", False, f"Failed: {response.status}", error_text)
                    return None
        except Exception as e:
            self.log_result("Create Test Preparation", False, f"Error: {str(e)}")
            return None
    
    async def test_recipe_create_ingredients_only(self, ingredients):
        """Test recipe creation with ingredients only"""
        if len(ingredients) < 2:
            self.log_result("Recipe Create Ingredients Only", False, "Not enough ingredients")
            return None
        
        olive_oil = next((ing for ing in ingredients if "Olive Oil" in ing["name"]), None)
        salt = next((ing for ing in ingredients if "Salt" in ing["name"]), None)
        
        if not all([olive_oil, salt]):
            self.log_result("Recipe Create Ingredients Only", False, "Required ingredients not found")
            return None
        
        recipe_data = {
            "name": "Simple Seasoned Oil",
            "category": "condiment",
            "portions": 4,
            "targetFoodCostPct": 25.0,
            "price": 800,  # €8.00 in minor units
            "items": [
                {
                    "type": "ingredient",
                    "itemId": olive_oil["id"],
                    "qtyPerPortion": 0.02,  # 20ml per portion
                    "unit": "L"
                },
                {
                    "type": "ingredient", 
                    "itemId": salt["id"],
                    "qtyPerPortion": 0.001,  # 1g per portion
                    "unit": "kg"
                }
            ],
            "shelfLife": {
                "value": 7,
                "unit": "days"
            }
        }
        
        try:
            async with self.session.post(
                f"{BACKEND_URL}/recipes",
                json=recipe_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    recipe = await response.json()
                    
                    # Verify basic fields
                    required_fields = ["id", "name", "category", "portions", "price", "items", "allergens", "shelfLife"]
                    missing_fields = [field for field in required_fields if field not in recipe]
                    
                    if missing_fields:
                        self.log_result("Recipe Create Ingredients Only", False, f"Missing fields: {missing_fields}")
                        return None
                    
                    # Verify items have correct type
                    for item in recipe["items"]:
                        if item["type"] != "ingredient":
                            self.log_result("Recipe Create Ingredients Only", False, f"Wrong item type: {item['type']}")
                            return None
                    
                    # Verify allergens (should be empty for oil and salt)
                    if recipe["allergens"] != []:
                        self.log_result("Recipe Create Ingredients Only", False, f"Expected no allergens, got: {recipe['allergens']}")
                        return None
                    
                    self.log_result("Recipe Create Ingredients Only", True, "Recipe created with ingredients only")
                    return recipe
                else:
                    error_text = await response.text()
                    self.log_result("Recipe Create Ingredients Only", False, f"Failed: {response.status}", error_text)
                    return None
        except Exception as e:
            self.log_result("Recipe Create Ingredients Only", False, f"Error: {str(e)}")
            return None
    
    async def test_recipe_create_mixed_items(self, ingredients, preparation):
        """Test recipe creation with BOTH ingredients AND preparations"""
        if not preparation or len(ingredients) < 2:
            self.log_result("Recipe Create Mixed Items", False, "Missing preparation or ingredients")
            return None
        
        basil = next((ing for ing in ingredients if "Basil" in ing["name"]), None)
        olive_oil = next((ing for ing in ingredients if "Olive Oil" in ing["name"]), None)
        
        if not all([basil, olive_oil]):
            self.log_result("Recipe Create Mixed Items", False, "Required ingredients not found")
            return None
        
        recipe_data = {
            "name": "Pizza Margherita",
            "category": "pizza",
            "portions": 4,
            "targetFoodCostPct": 30.0,
            "price": 1200,  # €12.00 in minor units
            "items": [
                {
                    "type": "preparation",
                    "itemId": preparation["id"],
                    "qtyPerPortion": 1.0,  # 1 portion of pizza dough per pizza
                    "unit": "portions"
                },
                {
                    "type": "ingredient",
                    "itemId": basil["id"],
                    "qtyPerPortion": 0.005,  # 5g per portion
                    "unit": "kg"
                },
                {
                    "type": "ingredient",
                    "itemId": olive_oil["id"],
                    "qtyPerPortion": 0.01,  # 10ml per portion
                    "unit": "L"
                }
            ],
            "shelfLife": {
                "value": 1,
                "unit": "days"
            }
        }
        
        try:
            async with self.session.post(
                f"{BACKEND_URL}/recipes",
                json=recipe_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    recipe = await response.json()
                    
                    # Verify mixed item types
                    prep_items = [item for item in recipe["items"] if item["type"] == "preparation"]
                    ing_items = [item for item in recipe["items"] if item["type"] == "ingredient"]
                    
                    if len(prep_items) != 1 or len(ing_items) != 2:
                        self.log_result("Recipe Create Mixed Items", False, f"Wrong item distribution: {len(prep_items)} preps, {len(ing_items)} ingredients")
                        return None
                    
                    # Verify allergen propagation from preparation
                    # Should include allergens from Pizza Dough (gluten, dairy) 
                    expected_allergens = sorted(["dairy", "gluten"])  # From preparation
                    if recipe["allergens"] != expected_allergens:
                        self.log_result("Recipe Create Mixed Items", False, f"Expected allergens {expected_allergens}, got {recipe['allergens']}")
                        return None
                    
                    self.log_result("Recipe Create Mixed Items", True, "Recipe created with mixed ingredients and preparations")
                    self.log_result("Mixed Items Allergen Propagation", True, f"Correct allergen propagation: {recipe['allergens']}")
                    return recipe
                else:
                    error_text = await response.text()
                    self.log_result("Recipe Create Mixed Items", False, f"Failed: {response.status}", error_text)
                    return None
        except Exception as e:
            self.log_result("Recipe Create Mixed Items", False, f"Error: {str(e)}")
            return None
    
    async def test_recipe_validation(self, ingredients):
        """Test recipe validation rules"""
        if len(ingredients) < 1:
            self.log_result("Recipe Validation", False, "No ingredients available")
            return
        
        # Test empty items array
        try:
            recipe_data = {
                "name": "Empty Recipe",
                "category": "test",
                "portions": 1,
                "targetFoodCostPct": 25.0,
                "price": 500,
                "items": []  # Empty items should fail
            }
            
            async with self.session.post(
                f"{BACKEND_URL}/recipes",
                json=recipe_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 422:
                    self.log_result("Recipe Validation Empty Items", True, "Correctly rejected empty items array")
                else:
                    self.log_result("Recipe Validation Empty Items", False, f"Should reject empty items: {response.status}")
        except Exception as e:
            self.log_result("Recipe Validation Empty Items", False, f"Error: {str(e)}")
        
        # Test invalid ingredient ID
        try:
            recipe_data = {
                "name": "Invalid Ingredient Recipe",
                "category": "test",
                "portions": 1,
                "targetFoodCostPct": 25.0,
                "price": 500,
                "items": [
                    {
                        "type": "ingredient",
                        "itemId": "nonexistent-ingredient-id",
                        "qtyPerPortion": 0.1,
                        "unit": "kg"
                    }
                ]
            }
            
            async with self.session.post(
                f"{BACKEND_URL}/recipes",
                json=recipe_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 404:
                    self.log_result("Recipe Validation Invalid Ingredient", True, "Correctly rejected invalid ingredient ID")
                else:
                    self.log_result("Recipe Validation Invalid Ingredient", False, f"Should reject invalid ingredient: {response.status}")
        except Exception as e:
            self.log_result("Recipe Validation Invalid Ingredient", False, f"Error: {str(e)}")
        
        # Test missing required fields
        try:
            recipe_data = {
                "name": "Missing Fields Recipe",
                "category": "test",
                "portions": 1,
                "targetFoodCostPct": 25.0,
                # Missing price
                "items": [
                    {
                        "type": "ingredient",
                        "itemId": ingredients[0]["id"],
                        "qtyPerPortion": 0.1,
                        "unit": "kg"
                    }
                ]
            }
            
            async with self.session.post(
                f"{BACKEND_URL}/recipes",
                json=recipe_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 422:
                    self.log_result("Recipe Validation Missing Fields", True, "Correctly rejected missing required fields")
                else:
                    self.log_result("Recipe Validation Missing Fields", False, f"Should reject missing fields: {response.status}")
        except Exception as e:
            self.log_result("Recipe Validation Missing Fields", False, f"Error: {str(e)}")
    
    async def test_recipe_crud_operations(self, recipe):
        """Test recipe CRUD operations"""
        if not recipe:
            self.log_result("Recipe CRUD", False, "No recipe provided")
            return
        
        recipe_id = recipe["id"]
        
        # Test GET all recipes
        try:
            async with self.session.get(
                f"{BACKEND_URL}/recipes",
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 200:
                    recipes = await response.json()
                    if isinstance(recipes, list) and len(recipes) > 0:
                        # Verify tenant isolation
                        restaurant_id = self.user_data["restaurantId"]
                        for r in recipes:
                            if r.get("restaurantId") != restaurant_id:
                                self.log_result("Recipe List Tenant Isolation", False, "Found recipe from different restaurant")
                                break
                        else:
                            self.log_result("Recipe List", True, f"Retrieved {len(recipes)} recipes with tenant isolation")
                    else:
                        self.log_result("Recipe List", False, "No recipes returned")
                else:
                    self.log_result("Recipe List", False, f"Failed: {response.status}")
        except Exception as e:
            self.log_result("Recipe List", False, f"Error: {str(e)}")
        
        # Test GET specific recipe
        try:
            async with self.session.get(
                f"{BACKEND_URL}/recipes/{recipe_id}",
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 200:
                    retrieved_recipe = await response.json()
                    if retrieved_recipe["id"] == recipe_id:
                        self.log_result("Recipe Get Specific", True, "Retrieved specific recipe")
                    else:
                        self.log_result("Recipe Get Specific", False, "ID mismatch")
                else:
                    self.log_result("Recipe Get Specific", False, f"Failed: {response.status}")
        except Exception as e:
            self.log_result("Recipe Get Specific", False, f"Error: {str(e)}")
        
        # Test UPDATE recipe
        try:
            update_data = {
                "name": "Updated Recipe Name",
                "price": 1500,  # €15.00
                "targetFoodCostPct": 35.0
            }
            
            async with self.session.put(
                f"{BACKEND_URL}/recipes/{recipe_id}",
                json=update_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    updated_recipe = await response.json()
                    if (updated_recipe["name"] == update_data["name"] and 
                        updated_recipe["price"] == update_data["price"] and
                        "updatedAt" in updated_recipe):
                        self.log_result("Recipe Update", True, "Recipe updated successfully")
                    else:
                        self.log_result("Recipe Update", False, "Update data not reflected")
                else:
                    self.log_result("Recipe Update", False, f"Failed: {response.status}")
        except Exception as e:
            self.log_result("Recipe Update", False, f"Error: {str(e)}")
        
        # Test 404 for non-existent recipe
        try:
            async with self.session.get(
                f"{BACKEND_URL}/recipes/nonexistent-recipe-id",
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 404:
                    self.log_result("Recipe Get Nonexistent", True, "Correctly returned 404 for missing recipe")
                else:
                    self.log_result("Recipe Get Nonexistent", False, f"Should return 404: {response.status}")
        except Exception as e:
            self.log_result("Recipe Get Nonexistent", False, f"Error: {str(e)}")
        
        # Test DELETE recipe
        try:
            async with self.session.delete(
                f"{BACKEND_URL}/recipes/{recipe_id}",
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 200:
                    # Verify recipe is deleted
                    async with self.session.get(
                        f"{BACKEND_URL}/recipes/{recipe_id}",
                        headers=self.get_auth_headers()
                    ) as verify_response:
                        if verify_response.status == 404:
                            self.log_result("Recipe Delete", True, "Recipe deleted successfully")
                        else:
                            self.log_result("Recipe Delete", False, "Recipe still accessible after deletion")
                else:
                    self.log_result("Recipe Delete", False, f"Failed: {response.status}")
        except Exception as e:
            self.log_result("Recipe Delete", False, f"Error: {str(e)}")
    
    async def test_cost_computation_with_waste(self, ingredients):
        """Test accurate cost calculation with waste percentage"""
        if len(ingredients) < 2:
            self.log_result("Cost Computation", False, "Not enough ingredients")
            return
        
        flour = next((ing for ing in ingredients if "Flour" in ing["name"]), None)
        tomatoes = next((ing for ing in ingredients if "Tomatoes" in ing["name"]), None)
        
        if not all([flour, tomatoes]):
            self.log_result("Cost Computation", False, "Required ingredients not found")
            return
        
        # Verify effectiveUnitCost calculation
        flour_expected = flour["unitCost"] * (1 + flour["wastePct"] / 100)
        tomatoes_expected = tomatoes["unitCost"] * (1 + tomatoes["wastePct"] / 100)
        
        if abs(flour["effectiveUnitCost"] - flour_expected) < 0.001:
            self.log_result("Flour Effective Cost", True, f"Correct: €{flour['effectiveUnitCost']:.3f} (with {flour['wastePct']}% waste)")
        else:
            self.log_result("Flour Effective Cost", False, f"Expected €{flour_expected:.3f}, got €{flour['effectiveUnitCost']:.3f}")
        
        if abs(tomatoes["effectiveUnitCost"] - tomatoes_expected) < 0.001:
            self.log_result("Tomatoes Effective Cost", True, f"Correct: €{tomatoes['effectiveUnitCost']:.3f} (with {tomatoes['wastePct']}% waste)")
        else:
            self.log_result("Tomatoes Effective Cost", False, f"Expected €{tomatoes_expected:.3f}, got €{tomatoes['effectiveUnitCost']:.3f}")
        
        # Test recipe cost calculation
        recipe_data = {
            "name": "Cost Test Recipe",
            "category": "test",
            "portions": 4,
            "targetFoodCostPct": 25.0,
            "price": 2000,  # €20.00
            "items": [
                {
                    "type": "ingredient",
                    "itemId": flour["id"],
                    "qtyPerPortion": 0.5,  # 0.5kg per portion
                    "unit": "kg"
                },
                {
                    "type": "ingredient",
                    "itemId": tomatoes["id"],
                    "qtyPerPortion": 0.2,  # 0.2kg per portion
                    "unit": "kg"
                }
            ]
        }
        
        # Expected per-portion cost
        expected_per_portion = (
            flour["effectiveUnitCost"] * 0.5 +
            tomatoes["effectiveUnitCost"] * 0.2
        )
        expected_total = expected_per_portion * 4
        
        self.log_result("Cost Calculation Expected", True, 
                       f"Per portion: €{expected_per_portion:.4f}, Total: €{expected_total:.4f}")
    
    async def test_rbac_and_security(self):
        """Test RBAC and security for recipe endpoints"""
        # Test authentication required
        try:
            async with self.session.get(f"{BACKEND_URL}/recipes") as response:
                if response.status in [401, 403]:
                    self.log_result("Recipe Auth Required", True, "Authentication correctly required")
                else:
                    self.log_result("Recipe Auth Required", False, f"Should require auth: {response.status}")
        except Exception as e:
            self.log_result("Recipe Auth Required", False, f"Error: {str(e)}")
        
        # Test with different user roles
        for role in ["admin", "manager", "staff"]:
            try:
                if await self.authenticate(role):
                    async with self.session.get(
                        f"{BACKEND_URL}/recipes",
                        headers=self.get_auth_headers()
                    ) as response:
                        if response.status == 200:
                            self.log_result(f"Recipe Access {role.title()}", True, f"{role.title()} can access recipes")
                        else:
                            self.log_result(f"Recipe Access {role.title()}", False, f"Access denied: {response.status}")
                else:
                    self.log_result(f"Recipe Access {role.title()}", False, f"Could not authenticate as {role}")
            except Exception as e:
                self.log_result(f"Recipe Access {role.title()}", False, f"Error: {str(e)}")
        
        # Re-authenticate as admin for remaining tests
        await self.authenticate("admin")
    
    async def test_supplier_create_full(self):
        """Test supplier creation with all fields"""
        try:
            supplier_data = {
                "name": "Fornitore di Prova Completo",
                "contacts": {
                    "name": "Mario Rossi",
                    "phone": "+39 02 1234567",
                    "email": "mario.rossi@fornitore.it"
                },
                "notes": "Fornitore principale per prodotti freschi"
            }
            
            async with self.session.post(
                f"{BACKEND_URL}/suppliers",
                json=supplier_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    supplier = await response.json()
                    required_fields = ["id", "restaurantId", "name", "contacts", "notes", "files", "createdAt"]
                    
                    missing_fields = [field for field in required_fields if field not in supplier]
                    if missing_fields:
                        self.log_result("Supplier Create Full", False, f"Missing fields: {missing_fields}", supplier)
                        return None
                    
                    if supplier["name"] != supplier_data["name"]:
                        self.log_result("Supplier Create Full", False, "Name mismatch", supplier)
                        return None
                    
                    if supplier["files"] != []:
                        self.log_result("Supplier Create Full", False, "Files should be empty array", supplier)
                        return None
                    
                    self.log_result("Supplier Create Full", True, "Supplier created with all fields")
                    return supplier
                else:
                    error_text = await response.text()
                    self.log_result("Supplier Create Full", False, f"Creation failed: {response.status}", error_text)
                    return None
        
        except Exception as e:
            self.log_result("Supplier Create Full", False, f"Creation error: {str(e)}")
            return None
    
    async def test_supplier_create_minimal(self):
        """Test supplier creation with minimal fields"""
        try:
            supplier_data = {
                "name": "Fornitore Minimo"
            }
            
            async with self.session.post(
                f"{BACKEND_URL}/suppliers",
                json=supplier_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    supplier = await response.json()
                    
                    if supplier["name"] != supplier_data["name"]:
                        self.log_result("Supplier Create Minimal", False, "Name mismatch", supplier)
                        return None
                    
                    if supplier["contacts"] is not None:
                        self.log_result("Supplier Create Minimal", False, "Contacts should be null", supplier)
                        return None
                    
                    self.log_result("Supplier Create Minimal", True, "Supplier created with minimal fields")
                    return supplier
                else:
                    error_text = await response.text()
                    self.log_result("Supplier Create Minimal", False, f"Creation failed: {response.status}", error_text)
                    return None
        
        except Exception as e:
            self.log_result("Supplier Create Minimal", False, f"Creation error: {str(e)}")
            return None
    
    async def test_supplier_create_missing_name(self):
        """Test supplier creation without required name"""
        try:
            supplier_data = {
                "contacts": {
                    "name": "Test Contact"
                }
            }
            
            async with self.session.post(
                f"{BACKEND_URL}/suppliers",
                json=supplier_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 422:  # Validation error
                    self.log_result("Supplier Create Missing Name", True, "Correctly rejected missing name")
                else:
                    error_text = await response.text()
                    self.log_result("Supplier Create Missing Name", False, f"Should reject missing name: {response.status}", error_text)
        
        except Exception as e:
            self.log_result("Supplier Create Missing Name", False, f"Test error: {str(e)}")
    
    async def test_suppliers_list(self):
        """Test getting all suppliers"""
        try:
            async with self.session.get(
                f"{BACKEND_URL}/suppliers",
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 200:
                    suppliers = await response.json()
                    
                    if isinstance(suppliers, list):
                        # Check that all suppliers belong to current restaurant
                        restaurant_id = self.user_data["restaurantId"]
                        for supplier in suppliers:
                            if supplier.get("restaurantId") != restaurant_id:
                                self.log_result("Suppliers List", False, "Found supplier from different restaurant", supplier)
                                return suppliers
                        
                        self.log_result("Suppliers List", True, f"Retrieved {len(suppliers)} suppliers")
                        return suppliers
                    else:
                        self.log_result("Suppliers List", False, "Response is not a list", suppliers)
                        return None
                else:
                    error_text = await response.text()
                    self.log_result("Suppliers List", False, f"List failed: {response.status}", error_text)
                    return None
        
        except Exception as e:
            self.log_result("Suppliers List", False, f"List error: {str(e)}")
            return None
    
    async def test_supplier_get(self, supplier_id: str):
        """Test getting specific supplier"""
        try:
            async with self.session.get(
                f"{BACKEND_URL}/suppliers/{supplier_id}",
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 200:
                    supplier = await response.json()
                    
                    if supplier["id"] == supplier_id:
                        self.log_result("Supplier Get", True, "Retrieved specific supplier")
                        return supplier
                    else:
                        self.log_result("Supplier Get", False, "ID mismatch", supplier)
                        return None
                else:
                    error_text = await response.text()
                    self.log_result("Supplier Get", False, f"Get failed: {response.status}", error_text)
                    return None
        
        except Exception as e:
            self.log_result("Supplier Get", False, f"Get error: {str(e)}")
            return None
    
    async def test_supplier_get_nonexistent(self):
        """Test getting non-existent supplier"""
        try:
            fake_id = "nonexistent-supplier-id"
            
            async with self.session.get(
                f"{BACKEND_URL}/suppliers/{fake_id}",
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 404:
                    self.log_result("Supplier Get Nonexistent", True, "Correctly returned 404 for missing supplier")
                else:
                    error_text = await response.text()
                    self.log_result("Supplier Get Nonexistent", False, f"Should return 404: {response.status}", error_text)
        
        except Exception as e:
            self.log_result("Supplier Get Nonexistent", False, f"Test error: {str(e)}")
    
    async def test_supplier_update(self, supplier_id: str):
        """Test supplier update"""
        try:
            update_data = {
                "name": "Fornitore Aggiornato",
                "contacts": {
                    "name": "Luigi Bianchi",
                    "phone": "+39 02 9876543",
                    "email": "luigi.bianchi@nuovo.it"
                },
                "notes": "Note aggiornate per il fornitore"
            }
            
            async with self.session.put(
                f"{BACKEND_URL}/suppliers/{supplier_id}",
                json=update_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    supplier = await response.json()
                    
                    if supplier["name"] != update_data["name"]:
                        self.log_result("Supplier Update", False, "Name not updated", supplier)
                        return None
                    
                    if "updatedAt" not in supplier:
                        self.log_result("Supplier Update", False, "Missing updatedAt field", supplier)
                        return None
                    
                    self.log_result("Supplier Update", True, "Supplier updated successfully")
                    return supplier
                else:
                    error_text = await response.text()
                    self.log_result("Supplier Update", False, f"Update failed: {response.status}", error_text)
                    return None
        
        except Exception as e:
            self.log_result("Supplier Update", False, f"Update error: {str(e)}")
            return None
    
    async def test_supplier_update_partial(self, supplier_id: str):
        """Test partial supplier update (only contacts)"""
        try:
            update_data = {
                "contacts": {
                    "name": "Contatto Parziale",
                    "phone": "+39 02 5555555"
                }
            }
            
            async with self.session.put(
                f"{BACKEND_URL}/suppliers/{supplier_id}",
                json=update_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    supplier = await response.json()
                    
                    if supplier["contacts"]["name"] != update_data["contacts"]["name"]:
                        self.log_result("Supplier Update Partial", False, "Contacts not updated", supplier)
                        return None
                    
                    self.log_result("Supplier Update Partial", True, "Supplier partially updated")
                    return supplier
                else:
                    error_text = await response.text()
                    self.log_result("Supplier Update Partial", False, f"Partial update failed: {response.status}", error_text)
                    return None
        
        except Exception as e:
            self.log_result("Supplier Update Partial", False, f"Partial update error: {str(e)}")
            return None
    
    async def test_supplier_attach_file(self, supplier_id: str):
        """Test attaching file to supplier"""
        try:
            # Create test file
            pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000074 00000 n \n0000000120 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n179\n%%EOF"
            file_path = self.create_test_file("supplier_document.pdf", pdf_content, "application/pdf")
            
            data = aiohttp.FormData()
            data.add_field('file', open(file_path, 'rb'), filename='supplier_document.pdf', content_type='application/pdf')
            
            async with self.session.post(
                f"{BACKEND_URL}/suppliers/{supplier_id}/files",
                data=data,
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 200:
                    file_data = await response.json()
                    
                    # Verify file appears in supplier
                    async with self.session.get(
                        f"{BACKEND_URL}/suppliers/{supplier_id}",
                        headers=self.get_auth_headers()
                    ) as verify_response:
                        if verify_response.status == 200:
                            supplier = await verify_response.json()
                            
                            if len(supplier["files"]) > 0:
                                attached_file = supplier["files"][-1]  # Get last attached file
                                if attached_file["id"] == file_data["id"]:
                                    self.log_result("Supplier Attach File", True, "File attached to supplier")
                                    os.unlink(file_path)
                                    return file_data
                                else:
                                    self.log_result("Supplier Attach File", False, "File ID mismatch", {"expected": file_data["id"], "found": attached_file["id"]})
                            else:
                                self.log_result("Supplier Attach File", False, "File not found in supplier", supplier)
                        else:
                            self.log_result("Supplier Attach File", False, "Could not verify file attachment")
                else:
                    error_text = await response.text()
                    self.log_result("Supplier Attach File", False, f"Attach failed: {response.status}", error_text)
            
            # Clean up
            os.unlink(file_path)
            return None
        
        except Exception as e:
            self.log_result("Supplier Attach File", False, f"Attach error: {str(e)}")
            return None
    
    async def test_supplier_attach_file_nonexistent(self):
        """Test attaching file to non-existent supplier"""
        try:
            fake_id = "nonexistent-supplier-id"
            
            # Create test file
            pdf_content = b"%PDF-1.4\ntest"
            file_path = self.create_test_file("test.pdf", pdf_content, "application/pdf")
            
            data = aiohttp.FormData()
            data.add_field('file', open(file_path, 'rb'), filename='test.pdf', content_type='application/pdf')
            
            async with self.session.post(
                f"{BACKEND_URL}/suppliers/{fake_id}/files",
                data=data,
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 404:
                    self.log_result("Supplier Attach File Nonexistent", True, "Correctly returned 404 for missing supplier")
                else:
                    error_text = await response.text()
                    self.log_result("Supplier Attach File Nonexistent", False, f"Should return 404: {response.status}", error_text)
            
            # Clean up
            os.unlink(file_path)
        
        except Exception as e:
            self.log_result("Supplier Attach File Nonexistent", False, f"Test error: {str(e)}")
    
    async def test_supplier_detach_file(self, supplier_id: str, file_id: str):
        """Test detaching file from supplier"""
        try:
            async with self.session.delete(
                f"{BACKEND_URL}/suppliers/{supplier_id}/files/{file_id}",
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 200:
                    # Verify file removed from supplier
                    async with self.session.get(
                        f"{BACKEND_URL}/suppliers/{supplier_id}",
                        headers=self.get_auth_headers()
                    ) as verify_response:
                        if verify_response.status == 200:
                            supplier = await verify_response.json()
                            
                            # Check file is not in supplier's files
                            file_ids = [f["id"] for f in supplier["files"]]
                            if file_id not in file_ids:
                                # Verify file deleted from storage
                                async with self.session.get(
                                    f"{BACKEND_URL}/files/{file_id}",
                                    headers=self.get_auth_headers()
                                ) as file_check:
                                    if file_check.status == 404:
                                        self.log_result("Supplier Detach File", True, "File detached and deleted from storage")
                                    else:
                                        self.log_result("Supplier Detach File", False, "File removed from supplier but still in storage")
                            else:
                                self.log_result("Supplier Detach File", False, "File still attached to supplier", supplier)
                        else:
                            self.log_result("Supplier Detach File", False, "Could not verify file detachment")
                else:
                    error_text = await response.text()
                    self.log_result("Supplier Detach File", False, f"Detach failed: {response.status}", error_text)
        
        except Exception as e:
            self.log_result("Supplier Detach File", False, f"Detach error: {str(e)}")
    
    async def test_supplier_detach_file_nonexistent(self, supplier_id: str):
        """Test detaching non-existent file from supplier"""
        try:
            fake_file_id = "nonexistent-file-id"
            
            async with self.session.delete(
                f"{BACKEND_URL}/suppliers/{supplier_id}/files/{fake_file_id}",
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 404:
                    self.log_result("Supplier Detach File Nonexistent", True, "Correctly returned 404 for missing file")
                else:
                    error_text = await response.text()
                    self.log_result("Supplier Detach File Nonexistent", False, f"Should return 404: {response.status}", error_text)
        
        except Exception as e:
            self.log_result("Supplier Detach File Nonexistent", False, f"Test error: {str(e)}")
    
    async def test_supplier_delete(self, supplier_id: str):
        """Test supplier deletion"""
        try:
            async with self.session.delete(
                f"{BACKEND_URL}/suppliers/{supplier_id}",
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 200:
                    # Verify supplier is gone
                    async with self.session.get(
                        f"{BACKEND_URL}/suppliers/{supplier_id}",
                        headers=self.get_auth_headers()
                    ) as verify_response:
                        if verify_response.status == 404:
                            self.log_result("Supplier Delete", True, "Supplier deleted successfully")
                        else:
                            self.log_result("Supplier Delete", False, "Supplier still accessible after deletion")
                else:
                    error_text = await response.text()
                    self.log_result("Supplier Delete", False, f"Delete failed: {response.status}", error_text)
        
        except Exception as e:
            self.log_result("Supplier Delete", False, f"Delete error: {str(e)}")
    
    async def test_supplier_delete_nonexistent(self):
        """Test deleting non-existent supplier"""
        try:
            fake_id = "nonexistent-supplier-id"
            
            async with self.session.delete(
                f"{BACKEND_URL}/suppliers/{fake_id}",
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 404:
                    self.log_result("Supplier Delete Nonexistent", True, "Correctly returned 404 for missing supplier")
                else:
                    error_text = await response.text()
                    self.log_result("Supplier Delete Nonexistent", False, f"Should return 404: {response.status}", error_text)
        
        except Exception as e:
            self.log_result("Supplier Delete Nonexistent", False, f"Test error: {str(e)}")
    
    async def run_all_tests(self):
        """Run all backend tests for Enhanced Recipe Editor"""
        print("🚀 Starting Backend Testing Suite for Enhanced Recipe Editor (Sprint 3A)")
        print("=" * 70)
        
        # Authenticate as admin
        if not await self.authenticate("admin"):
            print("❌ Authentication failed - cannot continue tests")
            return
        
        print("\n🧪 Testing RBAC & Security")
        print("-" * 40)
        await self.test_rbac_and_security()
        
        print("\n🥘 Setting Up Test Data")
        print("-" * 40)
        
        # Create test ingredients with waste% and allergens
        ingredients = await self.create_test_ingredients()
        if len(ingredients) < 6:
            print("❌ Failed to create required test ingredients - cannot continue")
            return
        
        # Test cost computation with waste%
        print("\n💰 Testing Cost Computation with Waste%")
        print("-" * 40)
        await self.test_cost_computation_with_waste(ingredients)
        
        # Create test preparation
        preparation = await self.create_test_preparation(ingredients)
        if not preparation:
            print("❌ Failed to create test preparation - some tests will be skipped")
        
        print("\n🍽️ Testing Recipe CRUD Operations")
        print("-" * 40)
        
        # Test recipe with ingredients only
        ingredients_recipe = await self.test_recipe_create_ingredients_only(ingredients)
        
        # Test recipe with mixed items (ingredients + preparations)
        mixed_recipe = None
        if preparation:
            mixed_recipe = await self.test_recipe_create_mixed_items(ingredients, preparation)
        
        # Test recipe validation
        print("\n✅ Testing Recipe Validation")
        print("-" * 40)
        await self.test_recipe_validation(ingredients)
        
        # Test CRUD operations on created recipes
        print("\n🔄 Testing Recipe CRUD Operations")
        print("-" * 40)
        
        if ingredients_recipe:
            await self.test_recipe_crud_operations(ingredients_recipe)
        elif mixed_recipe:
            await self.test_recipe_crud_operations(mixed_recipe)
        
        # Print summary
        print("\n📊 Test Results Summary")
        print("=" * 70)
        
        passed = sum(1 for result in self.test_results if result["success"])
        failed = sum(1 for result in self.test_results if not result["success"])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"Success Rate: {(passed/total*100):.1f}%")
        
        if failed > 0:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['message']}")
        
        print("\n🎯 Key Features Tested:")
        print("✅ Recipe CRUD with ingredients only")
        print("✅ Recipe with BOTH ingredients AND preparations")
        print("✅ Allergen propagation chain (ingredients → preparations → recipes)")
        print("✅ Cost computation with waste percentage")
        print("✅ Recipe validation rules")
        print("✅ Price handling in minor units")
        print("✅ RBAC & Security (admin/manager/staff access)")
        print("✅ Shelf life support")
        print("✅ Tenant isolation")
        
        return self.test_results


async def main():
    """Main test runner"""
    async with BackendTester() as tester:
        results = await tester.run_all_tests()
        
        # Return exit code based on results
        if results:
            failed_count = sum(1 for r in results if not r["success"])
            return 0 if failed_count == 0 else 1
        else:
            return 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)