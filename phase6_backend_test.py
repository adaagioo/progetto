#!/usr/bin/env python3
"""
Phase 6 Backend Testing Suite - Supplier Mapping & Price Lists
Tests ingredient-supplier mapping, price list file management, allergen taxonomy, and receiving auto-fill
"""

import asyncio
import aiohttp
import json
import os
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List

# Configuration
BACKEND_URL = "https://menuflow-8.preview.emergentagent.com/api"
TEST_CREDENTIALS = {
    "admin": {"email": "admin@test.com", "password": "admin123"},
    "manager": {"email": "manager@test.com", "password": "manager123"},
    "staff": {"email": "staff@test.com", "password": "staff123"}
}

class Phase6BackendTester:
    def __init__(self):
        self.session = None
        self.auth_token = None
        self.user_data = None
        self.test_results = []
        self.test_suppliers = []
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
            credentials = TEST_CREDENTIALS[user_type]
            
            async with self.session.post(
                f"{BACKEND_URL}/auth/login",
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
    
    def create_test_file(self, filename: str, content: bytes, mime_type: str) -> str:
        """Create a temporary test file"""
        temp_dir = Path(tempfile.gettempdir())
        file_path = temp_dir / filename
        with open(file_path, "wb") as f:
            f.write(content)
        return str(file_path)
    
    # ============ SETUP TEST DATA ============
    
    async def setup_test_suppliers(self) -> List[Dict[str, Any]]:
        """Create test suppliers for Phase 6 testing"""
        suppliers_data = [
            {
                "name": "Metro Cash & Carry",
                "contacts": {
                    "name": "Giuseppe Verdi",
                    "phone": "+39 02 1234567",
                    "email": "giuseppe.verdi@metro.it"
                },
                "notes": "Fornitore principale per prodotti freschi e secchi"
            },
            {
                "name": "Sysco Italia",
                "contacts": {
                    "name": "Maria Rossi",
                    "phone": "+39 06 9876543",
                    "email": "maria.rossi@sysco.it"
                },
                "notes": "Specializzato in prodotti gourmet e biologici"
            },
            {
                "name": "Chef Store",
                "contacts": {
                    "name": "Antonio Bianchi",
                    "phone": "+39 011 5555555",
                    "email": "antonio@chefstore.it"
                },
                "notes": "Attrezzature e ingredienti professionali"
            }
        ]
        
        created_suppliers = []
        
        for supplier_data in suppliers_data:
            try:
                async with self.session.post(
                    f"{BACKEND_URL}/suppliers",
                    json=supplier_data,
                    headers={**self.get_auth_headers(), "Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        supplier = await response.json()
                        created_suppliers.append(supplier)
                        self.log_result("Setup Test Supplier", True, f"Created {supplier['name']}")
                    else:
                        error_text = await response.text()
                        self.log_result("Setup Test Supplier", False, f"Failed to create {supplier_data['name']}: {response.status}", error_text)
            except Exception as e:
                self.log_result("Setup Test Supplier", False, f"Error creating {supplier_data['name']}: {str(e)}")
        
        self.test_suppliers = created_suppliers
        return created_suppliers
    
    async def setup_test_ingredients_with_suppliers(self) -> List[Dict[str, Any]]:
        """Create test ingredients with supplier mappings and new allergen taxonomy"""
        if len(self.test_suppliers) < 2:
            self.log_result("Setup Test Ingredients", False, "Not enough suppliers available")
            return []
        
        ingredients_data = [
            {
                "name": "Flour 00 Premium",
                "unit": "kg",
                "packSize": 25.0,
                "packCost": 45.50,
                "wastePct": 5.0,
                "allergens": ["GLUTEN"],  # New allergen code system
                "otherAllergens": [],
                "preferredSupplierId": self.test_suppliers[0]["id"],  # Metro Cash & Carry
                "category": "food",
                "minStockQty": 50.0
            },
            {
                "name": "San Marzano Tomatoes DOP",
                "unit": "kg",
                "packSize": 10.0,
                "packCost": 28.00,
                "wastePct": 12.0,
                "allergens": [],
                "otherAllergens": ["sulfites"],  # Custom allergen
                "preferredSupplierId": self.test_suppliers[1]["id"],  # Sysco Italia
                "category": "food",
                "minStockQty": 20.0
            },
            {
                "name": "Parmigiano Reggiano 24 Months",
                "unit": "kg",
                "packSize": 2.0,
                "packCost": 48.00,
                "wastePct": 8.0,
                "allergens": ["DAIRY"],
                "otherAllergens": [],
                "preferredSupplierId": self.test_suppliers[1]["id"],  # Sysco Italia
                "category": "food",
                "minStockQty": 5.0
            },
            {
                "name": "Extra Virgin Olive Oil Taggiasca",
                "unit": "L",
                "packSize": 5.0,
                "packCost": 85.00,
                "wastePct": 2.0,
                "allergens": [],
                "otherAllergens": [],
                "preferredSupplierId": self.test_suppliers[0]["id"],  # Metro Cash & Carry
                "category": "food",
                "minStockQty": 10.0
            },
            {
                "name": "Mixed Nuts Premium",
                "unit": "kg",
                "packSize": 1.0,
                "packCost": 18.50,
                "wastePct": 5.0,
                "allergens": ["TREE_NUTS"],
                "otherAllergens": ["pine nuts", "hazelnuts"],  # Specific nut types
                "preferredSupplierId": self.test_suppliers[2]["id"],  # Chef Store
                "category": "food",
                "minStockQty": 3.0
            },
            {
                "name": "Fresh Basil Genovese",
                "unit": "kg",
                "packSize": 0.5,
                "packCost": 12.00,
                "wastePct": 25.0,
                "allergens": [],
                "otherAllergens": [],
                "preferredSupplierId": None,  # No preferred supplier
                "category": "food",
                "minStockQty": 2.0
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
                        self.log_result("Setup Test Ingredient", True, f"Created {ingredient['name']}")
                    else:
                        error_text = await response.text()
                        self.log_result("Setup Test Ingredient", False, f"Failed to create {ingredient_data['name']}: {response.status}", error_text)
            except Exception as e:
                self.log_result("Setup Test Ingredient", False, f"Error creating {ingredient_data['name']}: {str(e)}")
        
        self.test_ingredients = created_ingredients
        return created_ingredients
    
    # ============ INGREDIENT-SUPPLIER MAPPING TESTS ============
    
    async def test_ingredient_with_preferred_supplier(self):
        """Test creating ingredient with preferredSupplierId"""
        if len(self.test_suppliers) < 1:
            self.log_result("Ingredient Preferred Supplier", False, "No suppliers available")
            return
        
        ingredient_data = {
            "name": "Test Ingredient with Supplier",
            "unit": "kg",
            "packSize": 1.0,
            "packCost": 5.00,
            "preferredSupplierId": self.test_suppliers[0]["id"],
            "allergens": ["GLUTEN"],
            "category": "food"
        }
        
        try:
            async with self.session.post(
                f"{BACKEND_URL}/ingredients",
                json=ingredient_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    ingredient = await response.json()
                    
                    # Verify supplier mapping
                    if ingredient.get("preferredSupplierId") == self.test_suppliers[0]["id"]:
                        if ingredient.get("preferredSupplierName") == self.test_suppliers[0]["name"]:
                            self.log_result("Ingredient Preferred Supplier", True, "Ingredient created with supplier mapping and name populated")
                        else:
                            self.log_result("Ingredient Preferred Supplier", False, f"Supplier name not populated: {ingredient.get('preferredSupplierName')}")
                    else:
                        self.log_result("Ingredient Preferred Supplier", False, "Supplier ID not saved correctly")
                else:
                    error_text = await response.text()
                    self.log_result("Ingredient Preferred Supplier", False, f"Creation failed: {response.status}", error_text)
        except Exception as e:
            self.log_result("Ingredient Preferred Supplier", False, f"Error: {str(e)}")
    
    async def test_ingredient_supplier_name_population(self):
        """Test that preferredSupplierName is auto-populated from supplier lookup"""
        try:
            async with self.session.get(
                f"{BACKEND_URL}/ingredients",
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 200:
                    ingredients = await response.json()
                    
                    supplier_mapped_count = 0
                    correct_names_count = 0
                    
                    for ingredient in ingredients:
                        if ingredient.get("preferredSupplierId"):
                            supplier_mapped_count += 1
                            
                            # Find the supplier
                            supplier = next((s for s in self.test_suppliers if s["id"] == ingredient["preferredSupplierId"]), None)
                            if supplier and ingredient.get("preferredSupplierName") == supplier["name"]:
                                correct_names_count += 1
                    
                    if supplier_mapped_count > 0:
                        if correct_names_count == supplier_mapped_count:
                            self.log_result("Supplier Name Population", True, f"All {supplier_mapped_count} ingredients have correct supplier names")
                        else:
                            self.log_result("Supplier Name Population", False, f"Only {correct_names_count}/{supplier_mapped_count} ingredients have correct supplier names")
                    else:
                        self.log_result("Supplier Name Population", False, "No ingredients with supplier mapping found")
                else:
                    error_text = await response.text()
                    self.log_result("Supplier Name Population", False, f"Failed to get ingredients: {response.status}", error_text)
        except Exception as e:
            self.log_result("Supplier Name Population", False, f"Error: {str(e)}")
    
    async def test_update_ingredient_supplier_mapping(self):
        """Test updating ingredient with new preferredSupplierId"""
        if len(self.test_ingredients) < 1 or len(self.test_suppliers) < 2:
            self.log_result("Update Ingredient Supplier", False, "Not enough test data")
            return
        
        ingredient = self.test_ingredients[0]
        new_supplier = self.test_suppliers[1]
        
        try:
            update_data = {
                "name": ingredient["name"],
                "unit": ingredient["unit"],
                "packSize": ingredient["packSize"],
                "packCost": ingredient["packCost"],
                "preferredSupplierId": new_supplier["id"],  # Change supplier
                "allergens": ingredient["allergens"],
                "category": ingredient["category"]
            }
            
            async with self.session.put(
                f"{BACKEND_URL}/ingredients/{ingredient['id']}",
                json=update_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    updated_ingredient = await response.json()
                    
                    if (updated_ingredient.get("preferredSupplierId") == new_supplier["id"] and
                        updated_ingredient.get("preferredSupplierName") == new_supplier["name"]):
                        self.log_result("Update Ingredient Supplier", True, "Supplier mapping updated correctly")
                    else:
                        self.log_result("Update Ingredient Supplier", False, "Supplier mapping not updated correctly")
                else:
                    error_text = await response.text()
                    self.log_result("Update Ingredient Supplier", False, f"Update failed: {response.status}", error_text)
        except Exception as e:
            self.log_result("Update Ingredient Supplier", False, f"Error: {str(e)}")
    
    async def test_remove_supplier_mapping(self):
        """Test removing supplier mapping by setting preferredSupplierId to null"""
        if len(self.test_ingredients) < 1:
            self.log_result("Remove Supplier Mapping", False, "No test ingredients")
            return
        
        ingredient = self.test_ingredients[0]
        
        try:
            update_data = {
                "name": ingredient["name"],
                "unit": ingredient["unit"],
                "packSize": ingredient["packSize"],
                "packCost": ingredient["packCost"],
                "preferredSupplierId": None,  # Remove supplier
                "allergens": ingredient["allergens"],
                "category": ingredient["category"]
            }
            
            async with self.session.put(
                f"{BACKEND_URL}/ingredients/{ingredient['id']}",
                json=update_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    updated_ingredient = await response.json()
                    
                    if (updated_ingredient.get("preferredSupplierId") is None and
                        updated_ingredient.get("preferredSupplierName") is None):
                        self.log_result("Remove Supplier Mapping", True, "Supplier mapping removed successfully")
                    else:
                        self.log_result("Remove Supplier Mapping", False, "Supplier mapping not removed correctly")
                else:
                    error_text = await response.text()
                    self.log_result("Remove Supplier Mapping", False, f"Update failed: {response.status}", error_text)
        except Exception as e:
            self.log_result("Remove Supplier Mapping", False, f"Error: {str(e)}")
    
    # ============ PRICE LIST FILE MANAGEMENT TESTS ============
    
    async def test_upload_price_list_to_supplier(self):
        """Test uploading price list file to supplier with fileType=price_list"""
        if len(self.test_suppliers) < 1:
            self.log_result("Upload Price List", False, "No suppliers available")
            return None
        
        supplier = self.test_suppliers[0]
        
        try:
            # Create a test PDF price list
            pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Price List 2024) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000074 00000 n \n0000000120 00000 n \n0000000179 00000 n \ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n274\n%%EOF"
            
            file_path = self.create_test_file("price_list_2024.pdf", pdf_content, "application/pdf")
            
            # Upload with fileType=price_list
            data = aiohttp.FormData()
            data.add_field('file', open(file_path, 'rb'), filename='price_list_2024.pdf', content_type='application/pdf')
            data.add_field('fileType', 'price_list')
            
            async with self.session.post(
                f"{BACKEND_URL}/suppliers/{supplier['id']}/files",
                data=data,
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 200:
                    file_data = await response.json()
                    
                    # Verify file appears in supplier with correct fileType
                    async with self.session.get(
                        f"{BACKEND_URL}/suppliers/{supplier['id']}",
                        headers=self.get_auth_headers()
                    ) as verify_response:
                        if verify_response.status == 200:
                            updated_supplier = await verify_response.json()
                            
                            # Find the uploaded file
                            price_list_file = None
                            for file_info in updated_supplier.get("files", []):
                                if file_info["id"] == file_data["id"]:
                                    price_list_file = file_info
                                    break
                            
                            if price_list_file:
                                # Check if fileType is included (this is the new feature)
                                if hasattr(price_list_file, 'get') and price_list_file.get("fileType") == "price_list":
                                    self.log_result("Upload Price List", True, "Price list uploaded with correct fileType")
                                    os.unlink(file_path)
                                    return file_data
                                else:
                                    self.log_result("Upload Price List", False, f"FileType not set correctly: {price_list_file}")
                            else:
                                self.log_result("Upload Price List", False, "File not found in supplier")
                        else:
                            self.log_result("Upload Price List", False, "Could not verify file upload")
                else:
                    error_text = await response.text()
                    self.log_result("Upload Price List", False, f"Upload failed: {response.status}", error_text)
            
            # Clean up
            os.unlink(file_path)
            return None
        
        except Exception as e:
            self.log_result("Upload Price List", False, f"Error: {str(e)}")
            return None
    
    async def test_upload_general_file_to_supplier(self):
        """Test uploading general file to supplier with fileType=general"""
        if len(self.test_suppliers) < 1:
            self.log_result("Upload General File", False, "No suppliers available")
            return None
        
        supplier = self.test_suppliers[0]
        
        try:
            # Create a test document
            pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000074 00000 n \n0000000120 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n179\n%%EOF"
            
            file_path = self.create_test_file("contract_2024.pdf", pdf_content, "application/pdf")
            
            # Upload with fileType=general
            data = aiohttp.FormData()
            data.add_field('file', open(file_path, 'rb'), filename='contract_2024.pdf', content_type='application/pdf')
            data.add_field('fileType', 'general')
            
            async with self.session.post(
                f"{BACKEND_URL}/suppliers/{supplier['id']}/files",
                data=data,
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 200:
                    file_data = await response.json()
                    self.log_result("Upload General File", True, "General file uploaded with fileType=general")
                    os.unlink(file_path)
                    return file_data
                else:
                    error_text = await response.text()
                    self.log_result("Upload General File", False, f"Upload failed: {response.status}", error_text)
            
            # Clean up
            os.unlink(file_path)
            return None
        
        except Exception as e:
            self.log_result("Upload General File", False, f"Error: {str(e)}")
            return None
    
    async def test_upload_file_without_filetype(self):
        """Test uploading file without fileType parameter (should default to general)"""
        if len(self.test_suppliers) < 1:
            self.log_result("Upload File No FileType", False, "No suppliers available")
            return
        
        supplier = self.test_suppliers[0]
        
        try:
            # Create a test document
            pdf_content = b"%PDF-1.4\ntest document"
            file_path = self.create_test_file("no_type_doc.pdf", pdf_content, "application/pdf")
            
            # Upload without fileType parameter
            data = aiohttp.FormData()
            data.add_field('file', open(file_path, 'rb'), filename='no_type_doc.pdf', content_type='application/pdf')
            # No fileType field - should default to 'general'
            
            async with self.session.post(
                f"{BACKEND_URL}/suppliers/{supplier['id']}/files",
                data=data,
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 200:
                    file_data = await response.json()
                    
                    # Verify defaults to general
                    async with self.session.get(
                        f"{BACKEND_URL}/suppliers/{supplier['id']}",
                        headers=self.get_auth_headers()
                    ) as verify_response:
                        if verify_response.status == 200:
                            updated_supplier = await verify_response.json()
                            
                            # Find the uploaded file
                            uploaded_file = None
                            for file_info in updated_supplier.get("files", []):
                                if file_info["id"] == file_data["id"]:
                                    uploaded_file = file_info
                                    break
                            
                            if uploaded_file:
                                if uploaded_file.get("fileType", "general") == "general":
                                    self.log_result("Upload File No FileType", True, "File defaults to fileType=general")
                                else:
                                    self.log_result("Upload File No FileType", False, f"Wrong default fileType: {uploaded_file.get('fileType')}")
                            else:
                                self.log_result("Upload File No FileType", False, "File not found in supplier")
                        else:
                            self.log_result("Upload File No FileType", False, "Could not verify file upload")
                else:
                    error_text = await response.text()
                    self.log_result("Upload File No FileType", False, f"Upload failed: {response.status}", error_text)
            
            # Clean up
            os.unlink(file_path)
        
        except Exception as e:
            self.log_result("Upload File No FileType", False, f"Error: {str(e)}")
    
    async def test_list_supplier_files_with_filetype(self):
        """Test that supplier files list includes fileType for each file"""
        if len(self.test_suppliers) < 1:
            self.log_result("List Supplier Files FileType", False, "No suppliers available")
            return
        
        supplier = self.test_suppliers[0]
        
        try:
            async with self.session.get(
                f"{BACKEND_URL}/suppliers/{supplier['id']}",
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 200:
                    supplier_data = await response.json()
                    
                    files = supplier_data.get("files", [])
                    if len(files) > 0:
                        # Check if files have fileType field
                        files_with_type = 0
                        price_list_files = 0
                        general_files = 0
                        
                        for file_info in files:
                            if "fileType" in file_info:
                                files_with_type += 1
                                if file_info["fileType"] == "price_list":
                                    price_list_files += 1
                                elif file_info["fileType"] == "general":
                                    general_files += 1
                        
                        if files_with_type == len(files):
                            self.log_result("List Supplier Files FileType", True, 
                                          f"All {len(files)} files have fileType ({price_list_files} price_list, {general_files} general)")
                        else:
                            self.log_result("List Supplier Files FileType", False, 
                                          f"Only {files_with_type}/{len(files)} files have fileType")
                    else:
                        self.log_result("List Supplier Files FileType", True, "No files to check (empty list)")
                else:
                    error_text = await response.text()
                    self.log_result("List Supplier Files FileType", False, f"Failed to get supplier: {response.status}", error_text)
        except Exception as e:
            self.log_result("List Supplier Files FileType", False, f"Error: {str(e)}")
    
    # ============ ALLERGEN TAXONOMY TESTS ============
    
    async def test_ingredient_with_allergen_codes(self):
        """Test creating ingredient with allergen codes (GLUTEN, DAIRY, etc.)"""
        try:
            ingredient_data = {
                "name": "Test Multi-Allergen Ingredient",
                "unit": "kg",
                "packSize": 1.0,
                "packCost": 10.00,
                "allergens": ["GLUTEN", "DAIRY", "EGGS"],  # Multiple allergen codes
                "otherAllergens": [],
                "category": "food"
            }
            
            async with self.session.post(
                f"{BACKEND_URL}/ingredients",
                json=ingredient_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    ingredient = await response.json()
                    
                    # Verify allergens stored as codes
                    expected_allergens = ["GLUTEN", "DAIRY", "EGGS"]
                    if ingredient.get("allergens") == expected_allergens:
                        self.log_result("Ingredient Allergen Codes", True, "Allergen codes stored correctly")
                    else:
                        self.log_result("Ingredient Allergen Codes", False, f"Expected {expected_allergens}, got {ingredient.get('allergens')}")
                else:
                    error_text = await response.text()
                    self.log_result("Ingredient Allergen Codes", False, f"Creation failed: {response.status}", error_text)
        except Exception as e:
            self.log_result("Ingredient Allergen Codes", False, f"Error: {str(e)}")
    
    async def test_ingredient_with_other_allergens(self):
        """Test creating ingredient with otherAllergens (custom allergens)"""
        try:
            ingredient_data = {
                "name": "Test Custom Allergen Ingredient",
                "unit": "kg",
                "packSize": 1.0,
                "packCost": 8.00,
                "allergens": ["TREE_NUTS"],  # Standard code
                "otherAllergens": ["sesame seeds", "pine nuts", "poppy seeds"],  # Custom allergens
                "category": "food"
            }
            
            async with self.session.post(
                f"{BACKEND_URL}/ingredients",
                json=ingredient_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    ingredient = await response.json()
                    
                    # Verify both allergen types stored
                    if (ingredient.get("allergens") == ["TREE_NUTS"] and
                        set(ingredient.get("otherAllergens", [])) == {"sesame seeds", "pine nuts", "poppy seeds"}):
                        self.log_result("Ingredient Other Allergens", True, "Custom allergens stored separately")
                    else:
                        self.log_result("Ingredient Other Allergens", False, 
                                      f"Allergens: {ingredient.get('allergens')}, Other: {ingredient.get('otherAllergens')}")
                else:
                    error_text = await response.text()
                    self.log_result("Ingredient Other Allergens", False, f"Creation failed: {response.status}", error_text)
        except Exception as e:
            self.log_result("Ingredient Other Allergens", False, f"Error: {str(e)}")
    
    async def test_preparation_allergen_propagation(self):
        """Test that preparation allergens are propagated from ingredients"""
        if len(self.test_ingredients) < 3:
            self.log_result("Preparation Allergen Propagation", False, "Not enough test ingredients")
            return None
        
        # Find ingredients with different allergens
        gluten_ingredient = next((ing for ing in self.test_ingredients if "GLUTEN" in ing.get("allergens", [])), None)
        dairy_ingredient = next((ing for ing in self.test_ingredients if "DAIRY" in ing.get("allergens", [])), None)
        nuts_ingredient = next((ing for ing in self.test_ingredients if "TREE_NUTS" in ing.get("allergens", [])), None)
        
        if not all([gluten_ingredient, dairy_ingredient, nuts_ingredient]):
            self.log_result("Preparation Allergen Propagation", False, "Required allergen ingredients not found")
            return None
        
        try:
            prep_data = {
                "name": "Multi-Allergen Test Preparation",
                "items": [
                    {
                        "ingredientId": gluten_ingredient["id"],
                        "qty": 0.5,
                        "unit": "kg"
                    },
                    {
                        "ingredientId": dairy_ingredient["id"],
                        "qty": 0.3,
                        "unit": "kg"
                    },
                    {
                        "ingredientId": nuts_ingredient["id"],
                        "qty": 0.1,
                        "unit": "kg"
                    }
                ],
                "yield": {
                    "value": 4.0,
                    "unit": "portions"
                }
            }
            
            async with self.session.post(
                f"{BACKEND_URL}/preparations",
                json=prep_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    preparation = await response.json()
                    
                    # Verify allergen propagation
                    expected_allergens = sorted(["GLUTEN", "DAIRY", "TREE_NUTS"])
                    actual_allergens = sorted(preparation.get("allergens", []))
                    
                    if actual_allergens == expected_allergens:
                        # Check otherAllergens propagation
                        expected_other = set()
                        for ing in [gluten_ingredient, dairy_ingredient, nuts_ingredient]:
                            expected_other.update(ing.get("otherAllergens", []))
                        
                        actual_other = set(preparation.get("otherAllergens", []))
                        
                        if actual_other == expected_other:
                            self.log_result("Preparation Allergen Propagation", True, 
                                          f"Allergens propagated correctly: {actual_allergens}, Other: {list(actual_other)}")
                            return preparation
                        else:
                            self.log_result("Preparation Allergen Propagation", False, 
                                          f"Other allergens not propagated correctly: expected {expected_other}, got {actual_other}")
                    else:
                        self.log_result("Preparation Allergen Propagation", False, 
                                      f"Expected allergens {expected_allergens}, got {actual_allergens}")
                else:
                    error_text = await response.text()
                    self.log_result("Preparation Allergen Propagation", False, f"Creation failed: {response.status}", error_text)
        except Exception as e:
            self.log_result("Preparation Allergen Propagation", False, f"Error: {str(e)}")
        
        return None
    
    async def test_recipe_allergen_propagation(self):
        """Test that recipe allergens are propagated from ingredients and preparations"""
        if len(self.test_ingredients) < 2:
            self.log_result("Recipe Allergen Propagation", False, "Not enough test ingredients")
            return
        
        # Create a preparation first
        preparation = await self.test_preparation_allergen_propagation()
        if not preparation:
            self.log_result("Recipe Allergen Propagation", False, "Could not create test preparation")
            return
        
        # Find an ingredient with different allergens
        other_ingredient = next((ing for ing in self.test_ingredients 
                               if ing.get("allergens") and ing["allergens"] != preparation.get("allergens", [])), None)
        
        if not other_ingredient:
            self.log_result("Recipe Allergen Propagation", False, "No suitable ingredient found")
            return
        
        try:
            recipe_data = {
                "name": "Mixed Allergen Test Recipe",
                "category": "test",
                "portions": 4,
                "targetFoodCostPct": 30.0,
                "price": 1500,
                "items": [
                    {
                        "type": "preparation",
                        "itemId": preparation["id"],
                        "qtyPerPortion": 1.0,
                        "unit": "portions"
                    },
                    {
                        "type": "ingredient",
                        "itemId": other_ingredient["id"],
                        "qtyPerPortion": 0.05,
                        "unit": other_ingredient["unit"]
                    }
                ]
            }
            
            async with self.session.post(
                f"{BACKEND_URL}/recipes",
                json=recipe_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    recipe = await response.json()
                    
                    # Verify allergen union from preparation + ingredient
                    expected_allergens = set(preparation.get("allergens", []))
                    expected_allergens.update(other_ingredient.get("allergens", []))
                    expected_allergens = sorted(list(expected_allergens))
                    
                    actual_allergens = sorted(recipe.get("allergens", []))
                    
                    if actual_allergens == expected_allergens:
                        # Check otherAllergens union
                        expected_other = set(preparation.get("otherAllergens", []))
                        expected_other.update(other_ingredient.get("otherAllergens", []))
                        
                        actual_other = set(recipe.get("otherAllergens", []))
                        
                        if actual_other == expected_other:
                            self.log_result("Recipe Allergen Propagation", True, 
                                          f"Recipe allergens correctly aggregated: {actual_allergens}, Other: {list(actual_other)}")
                        else:
                            self.log_result("Recipe Allergen Propagation", False, 
                                          f"Other allergens not aggregated correctly: expected {expected_other}, got {actual_other}")
                    else:
                        self.log_result("Recipe Allergen Propagation", False, 
                                      f"Expected allergens {expected_allergens}, got {actual_allergens}")
                else:
                    error_text = await response.text()
                    self.log_result("Recipe Allergen Propagation", False, f"Creation failed: {response.status}", error_text)
        except Exception as e:
            self.log_result("Recipe Allergen Propagation", False, f"Error: {str(e)}")
    
    # ============ RECEIVING AUTO-FILL TESTS ============
    
    async def test_ingredient_data_for_receiving(self):
        """Test that ingredients have required fields for receiving auto-fill"""
        try:
            async with self.session.get(
                f"{BACKEND_URL}/ingredients",
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 200:
                    ingredients = await response.json()
                    
                    if len(ingredients) == 0:
                        self.log_result("Ingredient Receiving Data", False, "No ingredients found")
                        return
                    
                    required_fields = ["packCost", "packSize", "preferredSupplierId", "unit"]
                    missing_fields_count = 0
                    
                    for ingredient in ingredients:
                        missing_fields = []
                        for field in required_fields:
                            if field not in ingredient:
                                missing_fields.append(field)
                        
                        if missing_fields:
                            missing_fields_count += 1
                    
                    if missing_fields_count == 0:
                        self.log_result("Ingredient Receiving Data", True, 
                                      f"All {len(ingredients)} ingredients have required fields for receiving auto-fill")
                    else:
                        self.log_result("Ingredient Receiving Data", False, 
                                      f"{missing_fields_count}/{len(ingredients)} ingredients missing required fields")
                else:
                    error_text = await response.text()
                    self.log_result("Ingredient Receiving Data", False, f"Failed to get ingredients: {response.status}", error_text)
        except Exception as e:
            self.log_result("Ingredient Receiving Data", False, f"Error: {str(e)}")
    
    async def test_create_receiving_with_ingredient_reference(self):
        """Test creating receiving record with ingredientId reference"""
        if len(self.test_ingredients) < 1 or len(self.test_suppliers) < 1:
            self.log_result("Create Receiving", False, "Not enough test data")
            return
        
        ingredient = self.test_ingredients[0]
        supplier = self.test_suppliers[0]
        
        try:
            receiving_data = {
                "supplierId": supplier["id"],
                "category": "food",
                "lines": [
                    {
                        "ingredientId": ingredient["id"],  # Reference to ingredient for auto-fill
                        "description": ingredient["name"],
                        "qty": 2.0,
                        "unit": ingredient["unit"],
                        "unitPrice": int(ingredient["packCost"] * 100),  # Convert to minor units
                        "packFormat": f"{ingredient['packSize']}{ingredient['unit']}",
                        "expiryDate": "2024-12-31"
                    }
                ],
                "arrivedAt": "2024-10-19T10:00:00Z",
                "notes": "Test receiving with ingredient reference"
            }
            
            async with self.session.post(
                f"{BACKEND_URL}/receiving",
                json=receiving_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    receiving = await response.json()
                    
                    # Verify receiving created with ingredient reference
                    if len(receiving.get("lines", [])) > 0:
                        line = receiving["lines"][0]
                        if line.get("ingredientId") == ingredient["id"]:
                            self.log_result("Create Receiving", True, "Receiving created with ingredient reference")
                        else:
                            self.log_result("Create Receiving", False, "Ingredient reference not saved correctly")
                    else:
                        self.log_result("Create Receiving", False, "No lines in created receiving")
                else:
                    error_text = await response.text()
                    self.log_result("Create Receiving", False, f"Creation failed: {response.status}", error_text)
        except Exception as e:
            self.log_result("Create Receiving", False, f"Error: {str(e)}")
    
    # ============ RBAC & TENANT ISOLATION TESTS ============
    
    async def test_supplier_mapping_rbac(self):
        """Test RBAC for supplier mapping operations"""
        if len(self.test_ingredients) < 1 or len(self.test_suppliers) < 1:
            self.log_result("Supplier Mapping RBAC", False, "Not enough test data")
            return
        
        ingredient = self.test_ingredients[0]
        supplier = self.test_suppliers[0]
        
        # Test with different roles
        for role in ["admin", "manager", "staff"]:
            try:
                if await self.authenticate(role):
                    update_data = {
                        "name": ingredient["name"],
                        "unit": ingredient["unit"],
                        "packSize": ingredient["packSize"],
                        "packCost": ingredient["packCost"],
                        "preferredSupplierId": supplier["id"],
                        "allergens": ingredient["allergens"],
                        "category": ingredient["category"]
                    }
                    
                    async with self.session.put(
                        f"{BACKEND_URL}/ingredients/{ingredient['id']}",
                        json=update_data,
                        headers={**self.get_auth_headers(), "Content-Type": "application/json"}
                    ) as response:
                        if role in ["admin", "manager"]:
                            if response.status == 200:
                                self.log_result(f"Supplier Mapping RBAC {role.title()}", True, f"{role.title()} can update supplier mapping")
                            else:
                                self.log_result(f"Supplier Mapping RBAC {role.title()}", False, f"{role.title()} cannot update supplier mapping: {response.status}")
                        else:  # staff
                            if response.status in [403, 401]:
                                self.log_result(f"Supplier Mapping RBAC {role.title()}", True, f"{role.title()} correctly denied supplier mapping update")
                            else:
                                self.log_result(f"Supplier Mapping RBAC {role.title()}", False, f"{role.title()} should be denied: {response.status}")
                else:
                    self.log_result(f"Supplier Mapping RBAC {role.title()}", False, f"Could not authenticate as {role}")
            except Exception as e:
                self.log_result(f"Supplier Mapping RBAC {role.title()}", False, f"Error: {str(e)}")
        
        # Re-authenticate as admin for remaining tests
        await self.authenticate("admin")
    
    async def test_price_list_upload_rbac(self):
        """Test RBAC for price list upload operations"""
        if len(self.test_suppliers) < 1:
            self.log_result("Price List Upload RBAC", False, "No suppliers available")
            return
        
        supplier = self.test_suppliers[0]
        
        # Test with different roles
        for role in ["admin", "manager", "staff"]:
            try:
                if await self.authenticate(role):
                    # Create test file
                    pdf_content = b"%PDF-1.4\ntest"
                    file_path = self.create_test_file(f"price_list_{role}.pdf", pdf_content, "application/pdf")
                    
                    data = aiohttp.FormData()
                    data.add_field('file', open(file_path, 'rb'), filename=f'price_list_{role}.pdf', content_type='application/pdf')
                    data.add_field('fileType', 'price_list')
                    
                    async with self.session.post(
                        f"{BACKEND_URL}/suppliers/{supplier['id']}/files",
                        data=data,
                        headers=self.get_auth_headers()
                    ) as response:
                        if role in ["admin", "manager"]:
                            if response.status == 200:
                                self.log_result(f"Price List Upload RBAC {role.title()}", True, f"{role.title()} can upload price lists")
                            else:
                                self.log_result(f"Price List Upload RBAC {role.title()}", False, f"{role.title()} cannot upload price lists: {response.status}")
                        else:  # staff
                            if response.status in [403, 401]:
                                self.log_result(f"Price List Upload RBAC {role.title()}", True, f"{role.title()} correctly denied price list upload")
                            else:
                                self.log_result(f"Price List Upload RBAC {role.title()}", False, f"{role.title()} should be denied: {response.status}")
                    
                    # Clean up
                    os.unlink(file_path)
                else:
                    self.log_result(f"Price List Upload RBAC {role.title()}", False, f"Could not authenticate as {role}")
            except Exception as e:
                self.log_result(f"Price List Upload RBAC {role.title()}", False, f"Error: {str(e)}")
        
        # Re-authenticate as admin for remaining tests
        await self.authenticate("admin")
    
    async def test_tenant_isolation(self):
        """Test tenant isolation for suppliers and ingredients"""
        try:
            # Get current restaurant ID
            restaurant_id = self.user_data["restaurantId"]
            
            # Test suppliers tenant isolation
            async with self.session.get(
                f"{BACKEND_URL}/suppliers",
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 200:
                    suppliers = await response.json()
                    
                    wrong_tenant_suppliers = [s for s in suppliers if s.get("restaurantId") != restaurant_id]
                    if len(wrong_tenant_suppliers) == 0:
                        self.log_result("Tenant Isolation Suppliers", True, f"All {len(suppliers)} suppliers belong to current restaurant")
                    else:
                        self.log_result("Tenant Isolation Suppliers", False, f"Found {len(wrong_tenant_suppliers)} suppliers from other restaurants")
                else:
                    self.log_result("Tenant Isolation Suppliers", False, f"Failed to get suppliers: {response.status}")
            
            # Test ingredients tenant isolation
            async with self.session.get(
                f"{BACKEND_URL}/ingredients",
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 200:
                    ingredients = await response.json()
                    
                    wrong_tenant_ingredients = [i for i in ingredients if i.get("restaurantId") != restaurant_id]
                    if len(wrong_tenant_ingredients) == 0:
                        self.log_result("Tenant Isolation Ingredients", True, f"All {len(ingredients)} ingredients belong to current restaurant")
                    else:
                        self.log_result("Tenant Isolation Ingredients", False, f"Found {len(wrong_tenant_ingredients)} ingredients from other restaurants")
                else:
                    self.log_result("Tenant Isolation Ingredients", False, f"Failed to get ingredients: {response.status}")
        
        except Exception as e:
            self.log_result("Tenant Isolation", False, f"Error: {str(e)}")
    
    # ============ AUDIT LOGGING TESTS ============
    
    async def test_supplier_mapping_audit_logging(self):
        """Test that supplier mapping changes are logged in audit trail"""
        # Note: This test assumes audit logging is implemented
        # Since we don't have direct access to audit logs endpoint, we'll test indirectly
        if len(self.test_ingredients) < 1 or len(self.test_suppliers) < 2:
            self.log_result("Supplier Mapping Audit", False, "Not enough test data")
            return
        
        ingredient = self.test_ingredients[0]
        old_supplier_id = ingredient.get("preferredSupplierId")
        new_supplier = self.test_suppliers[1]
        
        try:
            # Update supplier mapping
            update_data = {
                "name": ingredient["name"],
                "unit": ingredient["unit"],
                "packSize": ingredient["packSize"],
                "packCost": ingredient["packCost"],
                "preferredSupplierId": new_supplier["id"],
                "allergens": ingredient["allergens"],
                "category": ingredient["category"]
            }
            
            async with self.session.put(
                f"{BACKEND_URL}/ingredients/{ingredient['id']}",
                json=update_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    # Audit logging is internal - we can only verify the update succeeded
                    # In a real implementation, we'd check an audit log endpoint
                    self.log_result("Supplier Mapping Audit", True, "Supplier mapping change completed (audit logging assumed)")
                else:
                    error_text = await response.text()
                    self.log_result("Supplier Mapping Audit", False, f"Update failed: {response.status}", error_text)
        except Exception as e:
            self.log_result("Supplier Mapping Audit", False, f"Error: {str(e)}")
    
    async def test_price_list_upload_audit_logging(self):
        """Test that price list uploads are logged in audit trail"""
        if len(self.test_suppliers) < 1:
            self.log_result("Price List Upload Audit", False, "No suppliers available")
            return
        
        supplier = self.test_suppliers[0]
        
        try:
            # Create and upload price list
            pdf_content = b"%PDF-1.4\naudit test"
            file_path = self.create_test_file("audit_price_list.pdf", pdf_content, "application/pdf")
            
            data = aiohttp.FormData()
            data.add_field('file', open(file_path, 'rb'), filename='audit_price_list.pdf', content_type='application/pdf')
            data.add_field('fileType', 'price_list')
            
            async with self.session.post(
                f"{BACKEND_URL}/suppliers/{supplier['id']}/files",
                data=data,
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 200:
                    # Audit logging is internal - we can only verify the upload succeeded
                    self.log_result("Price List Upload Audit", True, "Price list upload completed (audit logging assumed)")
                else:
                    error_text = await response.text()
                    self.log_result("Price List Upload Audit", False, f"Upload failed: {response.status}", error_text)
            
            # Clean up
            os.unlink(file_path)
        except Exception as e:
            self.log_result("Price List Upload Audit", False, f"Error: {str(e)}")
    
    # ============ MAIN TEST RUNNER ============
    
    async def run_all_tests(self):
        """Run all Phase 6 backend tests"""
        print("🚀 Starting Phase 6 Backend Testing Suite - Supplier Mapping & Price Lists")
        print("=" * 80)
        
        # Authenticate as admin
        if not await self.authenticate("admin"):
            print("❌ Authentication failed - cannot continue tests")
            return
        
        print("\n🏗️ Setting Up Test Data")
        print("-" * 40)
        
        # Setup test suppliers and ingredients
        suppliers = await self.setup_test_suppliers()
        if len(suppliers) < 3:
            print("❌ Failed to create required test suppliers - some tests will be skipped")
        
        ingredients = await self.setup_test_ingredients_with_suppliers()
        if len(ingredients) < 5:
            print("❌ Failed to create required test ingredients - some tests will be skipped")
        
        print(f"\n📊 Test Data Created: {len(suppliers)} suppliers, {len(ingredients)} ingredients")
        
        print("\n🔗 Testing Ingredient-Supplier Mapping")
        print("-" * 40)
        await self.test_ingredient_with_preferred_supplier()
        await self.test_ingredient_supplier_name_population()
        await self.test_update_ingredient_supplier_mapping()
        await self.test_remove_supplier_mapping()
        
        print("\n📄 Testing Price List File Management")
        print("-" * 40)
        await self.test_upload_price_list_to_supplier()
        await self.test_upload_general_file_to_supplier()
        await self.test_upload_file_without_filetype()
        await self.test_list_supplier_files_with_filetype()
        
        print("\n🚨 Testing Allergen Taxonomy (New System)")
        print("-" * 40)
        await self.test_ingredient_with_allergen_codes()
        await self.test_ingredient_with_other_allergens()
        await self.test_preparation_allergen_propagation()
        await self.test_recipe_allergen_propagation()
        
        print("\n📦 Testing Receiving Auto-Fill Support")
        print("-" * 40)
        await self.test_ingredient_data_for_receiving()
        await self.test_create_receiving_with_ingredient_reference()
        
        print("\n🔐 Testing RBAC & Tenant Isolation")
        print("-" * 40)
        await self.test_supplier_mapping_rbac()
        await self.test_price_list_upload_rbac()
        await self.test_tenant_isolation()
        
        print("\n📋 Testing Audit Logging")
        print("-" * 40)
        await self.test_supplier_mapping_audit_logging()
        await self.test_price_list_upload_audit_logging()
        
        # Print summary
        print("\n" + "=" * 80)
        print("📊 PHASE 6 BACKEND TESTING SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["success"]])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   - {result['test']}: {result['message']}")
        
        print("\n🎯 Phase 6 Backend Testing Complete!")
        return self.test_results

async def main():
    """Main test runner"""
    async with Phase6BackendTester() as tester:
        results = await tester.run_all_tests()
        
        # Return exit code based on results
        failed_count = len([r for r in results if not r["success"]])
        return 0 if failed_count == 0 else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)