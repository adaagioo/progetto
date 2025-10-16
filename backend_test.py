#!/usr/bin/env python3
"""
Backend Testing Suite for Suppliers Module
Tests file upload/download, suppliers CRUD, and file attachments
"""

import asyncio
import aiohttp
import json
import os
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

# Configuration
BACKEND_URL = "https://ristobrain.preview.emergentagent.com/api"
TEST_CREDENTIALS = {
    "admin": {"email": "admin@test.com", "password": "password123"},
    "restaurant": {"email": "ristorante1", "password": "password123"}
}

class BackendTester:
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
                "password": "password123",
                "displayName": "Test Admin",
                "restaurantName": "Test Restaurant",
                "locale": "en-US"
            }
            
            async with self.session.post(
                f"{BACKEND_URL}/auth/register",
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
    
    async def test_file_upload_valid(self):
        """Test valid file upload"""
        try:
            # Create a test PDF file
            pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000074 00000 n \n0000000120 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n179\n%%EOF"
            
            file_path = self.create_test_file("test_document.pdf", pdf_content, "application/pdf")
            
            # Upload file
            data = aiohttp.FormData()
            data.add_field('file', open(file_path, 'rb'), filename='test_document.pdf', content_type='application/pdf')
            data.add_field('subfolder', 'general')
            
            async with self.session.post(
                f"{BACKEND_URL}/files/upload",
                data=data,
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 200:
                    file_data = await response.json()
                    required_fields = ["id", "filename", "path", "size", "mimeType", "hash", "uploadedBy", "uploadedAt"]
                    
                    missing_fields = [field for field in required_fields if field not in file_data]
                    if missing_fields:
                        self.log_result("File Upload Valid", False, f"Missing fields: {missing_fields}", file_data)
                        return None
                    
                    if file_data["mimeType"] != "application/pdf":
                        self.log_result("File Upload Valid", False, f"Wrong MIME type: {file_data['mimeType']}")
                        return None
                    
                    self.log_result("File Upload Valid", True, "PDF file uploaded successfully")
                    return file_data
                else:
                    error_text = await response.text()
                    self.log_result("File Upload Valid", False, f"Upload failed: {response.status}", error_text)
                    return None
            
            # Clean up
            os.unlink(file_path)
            
        except Exception as e:
            self.log_result("File Upload Valid", False, f"Upload error: {str(e)}")
            return None
    
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
        """Run all backend tests"""
        print("🚀 Starting Backend Testing Suite for Suppliers Module")
        print("=" * 60)
        
        # Authenticate (register if needed)
        if not await self.register_test_user():
            print("❌ Authentication failed - cannot continue tests")
            return
        
        print("\n📁 Testing File Upload/Download Endpoints")
        print("-" * 40)
        
        # Test file operations
        uploaded_file = await self.test_file_upload_valid()
        await self.test_file_upload_invalid_mime()
        await self.test_file_upload_oversized()
        await self.test_file_download_nonexistent()
        
        if uploaded_file:
            await self.test_file_download(uploaded_file)
            await self.test_file_delete(uploaded_file)
        
        print("\n👥 Testing Suppliers CRUD Endpoints")
        print("-" * 40)
        
        # Test supplier CRUD
        full_supplier = await self.test_supplier_create_full()
        minimal_supplier = await self.test_supplier_create_minimal()
        await self.test_supplier_create_missing_name()
        
        suppliers_list = await self.test_suppliers_list()
        
        if full_supplier:
            supplier_id = full_supplier["id"]
            await self.test_supplier_get(supplier_id)
            await self.test_supplier_update(supplier_id)
            await self.test_supplier_update_partial(supplier_id)
            
            # Test file attachments
            print("\n📎 Testing Supplier File Attachments")
            print("-" * 40)
            
            attached_file = await self.test_supplier_attach_file(supplier_id)
            await self.test_supplier_attach_file_nonexistent()
            
            if attached_file:
                await self.test_supplier_detach_file(supplier_id, attached_file["id"])
            
            await self.test_supplier_detach_file_nonexistent(supplier_id)
            
            # Clean up - delete supplier
            await self.test_supplier_delete(supplier_id)
        
        if minimal_supplier:
            await self.test_supplier_delete(minimal_supplier["id"])
        
        await self.test_supplier_get_nonexistent()
        await self.test_supplier_delete_nonexistent()
        
        # Print summary
        print("\n📊 Test Results Summary")
        print("=" * 60)
        
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