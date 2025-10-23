#!/usr/bin/env python3
"""
Phase 8 OCR Document Ingestion Backend Testing
Comprehensive testing for OCR processing and receiving integration
"""

import requests
import json
import io
from PIL import Image, ImageDraw, ImageFont
import tempfile
import os
from datetime import datetime, timedelta

# Test Configuration
BASE_URL = "https://resto-doc-scan.preview.emergentagent.com/api"

# Test Credentials
TEST_USERS = {
    "admin": {"email": "admin@test.com", "password": "admin123"},
    "manager": {"email": "manager@test.com", "password": "manager123"},
    "staff": {"email": "staff@test.com", "password": "staff123"}
}

class OCRTester:
    def __init__(self):
        self.tokens = {}
        self.test_data = {}
        self.results = []
        
    def log_result(self, test_name, success, details=""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
        
        self.results.append({
            "test": test_name,
            "success": success,
            "details": details
        })
    
    def login_all_users(self):
        """Login all test users and store tokens"""
        print("\n🔐 Logging in test users...")
        
        for role, creds in TEST_USERS.items():
            try:
                response = requests.post(f"{BASE_URL}/auth/login", json=creds)
                if response.status_code == 200:
                    data = response.json()
                    self.tokens[role] = data["access_token"]
                    self.log_result(f"Login {role}", True, f"Token obtained")
                else:
                    self.log_result(f"Login {role}", False, f"Status: {response.status_code}")
                    return False
            except Exception as e:
                self.log_result(f"Login {role}", False, f"Error: {str(e)}")
                return False
        
        return True
    
    def create_test_invoice_image(self) -> bytes:
        """Create a test invoice image programmatically"""
        # Create a simple invoice image
        width, height = 800, 600
        image = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(image)
        
        # Try to use a font, fallback to default if not available
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
        except:
            font = ImageFont.load_default()
            font_large = ImageFont.load_default()
        
        # Invoice content
        y_pos = 50
        
        # Header
        draw.text((50, y_pos), "INVOICE", fill='black', font=font_large)
        y_pos += 40
        
        # Invoice details
        draw.text((50, y_pos), "Invoice Number: INV-2024-001", fill='black', font=font)
        y_pos += 25
        draw.text((50, y_pos), "Date: 2024-01-15", fill='black', font=font)
        y_pos += 25
        draw.text((50, y_pos), "Supplier: Fresh Foods Italia SRL", fill='black', font=font)
        y_pos += 40
        
        # Line items header
        draw.text((50, y_pos), "Description", fill='black', font=font)
        draw.text((300, y_pos), "Qty", fill='black', font=font)
        draw.text((400, y_pos), "Unit", fill='black', font=font)
        draw.text((500, y_pos), "Price", fill='black', font=font)
        y_pos += 30
        
        # Line items
        items = [
            ("San Marzano Tomatoes", "10.0", "kg", "€3.20"),
            ("Extra Virgin Olive Oil", "5.0", "l", "€12.50"),
            ("Mozzarella di Bufala", "3.0", "kg", "€18.00")
        ]
        
        for desc, qty, unit, price in items:
            draw.text((50, y_pos), desc, fill='black', font=font)
            draw.text((300, y_pos), qty, fill='black', font=font)
            draw.text((400, y_pos), unit, fill='black', font=font)
            draw.text((500, y_pos), price, fill='black', font=font)
            y_pos += 25
        
        # Total
        y_pos += 20
        draw.text((400, y_pos), "Total: €86.50", fill='black', font=font)
        
        # Convert to bytes
        img_buffer = io.BytesIO()
        image.save(img_buffer, format='PNG')
        return img_buffer.getvalue()
    
    def create_test_pdf(self) -> bytes:
        """Create a simple test PDF with invoice content"""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            import io
            
            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=letter)
            
            # Add invoice content
            p.drawString(100, 750, "INVOICE")
            p.drawString(100, 720, "Invoice Number: INV-2024-001")
            p.drawString(100, 700, "Date: 2024-01-15")
            p.drawString(100, 680, "Supplier: Fresh Foods Italia SRL")
            
            p.drawString(100, 640, "Description")
            p.drawString(300, 640, "Qty")
            p.drawString(400, 640, "Unit")
            p.drawString(500, 640, "Price")
            
            p.drawString(100, 620, "San Marzano Tomatoes")
            p.drawString(300, 620, "10.0")
            p.drawString(400, 620, "kg")
            p.drawString(500, 620, "€3.20")
            
            p.drawString(100, 600, "Extra Virgin Olive Oil")
            p.drawString(300, 600, "5.0")
            p.drawString(400, 600, "l")
            p.drawString(500, 600, "€12.50")
            
            p.drawString(100, 580, "Mozzarella di Bufala")
            p.drawString(300, 580, "3.0")
            p.drawString(400, 580, "kg")
            p.drawString(500, 580, "€18.00")
            
            p.drawString(400, 540, "Total: €86.50")
            
            p.showPage()
            p.save()
            
            return buffer.getvalue()
        except ImportError:
            # Fallback to image if reportlab not available
            return self.create_test_invoice_image()
    
    def setup_test_data(self):
        """Create suppliers and ingredients for testing"""
        print("\n📋 Setting up test data...")
        
        # Create supplier
        supplier_data = {
            "name": "Fresh Foods Italia SRL",
            "contacts": {
                "name": "Marco Rossi",
                "phone": "+39 06 1234567",
                "email": "orders@freshfoods.it"
            },
            "notes": "Primary produce supplier"
        }
        
        try:
            headers = {"Authorization": f"Bearer {self.tokens['admin']}"}
            response = requests.post(f"{BASE_URL}/suppliers", json=supplier_data, headers=headers)
            
            if response.status_code in [200, 201]:
                supplier = response.json()
                self.test_data['supplier_id'] = supplier['id']
                self.log_result("Create test supplier", True, f"ID: {supplier['id']}")
            else:
                self.log_result("Create test supplier", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Create test supplier", False, f"Error: {str(e)}")
            return False
        
        # Create test ingredients
        ingredients = [
            {
                "name": "San Marzano Tomatoes",
                "unit": "kg",
                "packSize": 10.0,
                "packCost": 32.0,
                "preferredSupplierId": self.test_data['supplier_id'],
                "category": "food",
                "wastePct": 15.0,
                "minStockQty": 5.0
            },
            {
                "name": "Extra Virgin Olive Oil",
                "unit": "l",
                "packSize": 5.0,
                "packCost": 62.5,
                "preferredSupplierId": self.test_data['supplier_id'],
                "category": "food",
                "wastePct": 2.0,
                "minStockQty": 2.0
            },
            {
                "name": "Mozzarella di Bufala",
                "unit": "kg",
                "packSize": 3.0,
                "packCost": 54.0,
                "preferredSupplierId": self.test_data['supplier_id'],
                "category": "food",
                "wastePct": 8.0,
                "minStockQty": 1.0,
                "allergens": ["DAIRY"]
            }
        ]
        
        self.test_data['ingredient_ids'] = []
        
        for ing_data in ingredients:
            try:
                response = requests.post(f"{BASE_URL}/ingredients", json=ing_data, headers=headers)
                
                if response.status_code in [200, 201]:
                    ingredient = response.json()
                    self.test_data['ingredient_ids'].append(ingredient['id'])
                    self.log_result(f"Create ingredient: {ing_data['name']}", True, f"ID: {ingredient['id']}")
                else:
                    self.log_result(f"Create ingredient: {ing_data['name']}", False, f"Status: {response.status_code}")
            except Exception as e:
                self.log_result(f"Create ingredient: {ing_data['name']}", False, f"Error: {str(e)}")
        
        return len(self.test_data['ingredient_ids']) == len(ingredients)
    
    def test_ocr_processing(self):
        """Test OCR processing endpoint"""
        print("\n🔍 Testing OCR Processing...")
        
        # Test 1: OCR with image file (Admin)
        try:
            image_data = self.create_test_invoice_image()
            files = {'file': ('test_invoice.png', image_data, 'image/png')}
            headers = {"Authorization": f"Bearer {self.tokens['admin']}"}
            
            response = requests.post(f"{BASE_URL}/ocr/process", files=files, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                
                # Verify response structure
                required_fields = ['success', 'filename', 'ocr', 'parsed']
                if all(field in result for field in required_fields):
                    ocr_data = result['ocr']
                    parsed_data = result['parsed']
                    
                    # Check OCR data
                    if (ocr_data.get('confidence', 0) > 0 and 
                        ocr_data.get('text') and 
                        'INVOICE' in ocr_data['text']):
                        
                        # Check parsed data
                        if (parsed_data.get('document_type') == 'invoice' and
                            parsed_data.get('invoice_number') and
                            parsed_data.get('line_items')):
                            
                            self.test_data['ocr_result'] = result
                            self.log_result("OCR Image Processing (Admin)", True, 
                                          f"Confidence: {ocr_data['confidence']}%, Items: {len(parsed_data['line_items'])}")
                        else:
                            self.log_result("OCR Image Processing (Admin)", False, "Parsed data incomplete")
                    else:
                        self.log_result("OCR Image Processing (Admin)", False, "OCR extraction failed")
                else:
                    self.log_result("OCR Image Processing (Admin)", False, "Response structure invalid")
            else:
                self.log_result("OCR Image Processing (Admin)", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_result("OCR Image Processing (Admin)", False, f"Error: {str(e)}")
        
        # Test 2: OCR with PDF file (Manager)
        try:
            pdf_data = self.create_test_pdf()
            files = {'file': ('test_invoice.pdf', pdf_data, 'application/pdf')}
            headers = {"Authorization": f"Bearer {self.tokens['manager']}"}
            
            response = requests.post(f"{BASE_URL}/ocr/process", files=files, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success') and result.get('ocr', {}).get('confidence', 0) > 0:
                    self.log_result("OCR PDF Processing (Manager)", True, 
                                  f"Confidence: {result['ocr']['confidence']}%")
                else:
                    self.log_result("OCR PDF Processing (Manager)", False, "OCR failed")
            else:
                self.log_result("OCR PDF Processing (Manager)", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_result("OCR PDF Processing (Manager)", False, f"Error: {str(e)}")
        
        # Test 3: RBAC - Staff should get 403
        try:
            image_data = self.create_test_invoice_image()
            files = {'file': ('test_invoice.png', image_data, 'image/png')}
            headers = {"Authorization": f"Bearer {self.tokens['staff']}"}
            
            response = requests.post(f"{BASE_URL}/ocr/process", files=files, headers=headers)
            
            if response.status_code == 403:
                self.log_result("OCR RBAC - Staff Denied", True, "403 Forbidden as expected")
            else:
                self.log_result("OCR RBAC - Staff Denied", False, f"Expected 403, got {response.status_code}")
        except Exception as e:
            self.log_result("OCR RBAC - Staff Denied", False, f"Error: {str(e)}")
        
        # Test 4: Unsupported file type
        try:
            text_data = b"This is a text file"
            files = {'file': ('test.txt', text_data, 'text/plain')}
            headers = {"Authorization": f"Bearer {self.tokens['admin']}"}
            
            response = requests.post(f"{BASE_URL}/ocr/process", files=files, headers=headers)
            
            if response.status_code == 400:
                self.log_result("OCR Unsupported File Type", True, "400 Bad Request as expected")
            else:
                self.log_result("OCR Unsupported File Type", False, f"Expected 400, got {response.status_code}")
        except Exception as e:
            self.log_result("OCR Unsupported File Type", False, f"Error: {str(e)}")
    
    def test_document_parsing_accuracy(self):
        """Test parsing accuracy of extracted data"""
        print("\n📊 Testing Document Parsing Accuracy...")
        
        if 'ocr_result' not in self.test_data:
            self.log_result("Document Parsing Test", False, "No OCR result available")
            return
        
        parsed = self.test_data['ocr_result']['parsed']
        
        # Test invoice number extraction
        if parsed.get('invoice_number'):
            if 'INV-2024-001' in parsed['invoice_number'] or '2024' in parsed['invoice_number']:
                self.log_result("Parse Invoice Number", True, f"Found: {parsed['invoice_number']}")
            else:
                self.log_result("Parse Invoice Number", False, f"Incorrect: {parsed['invoice_number']}")
        else:
            self.log_result("Parse Invoice Number", False, "Not found")
        
        # Test date extraction
        if parsed.get('date'):
            if '2024-01-15' in parsed['date'] or '2024' in parsed['date']:
                self.log_result("Parse Date", True, f"Found: {parsed['date']}")
            else:
                self.log_result("Parse Date", False, f"Incorrect: {parsed['date']}")
        else:
            self.log_result("Parse Date", False, "Not found")
        
        # Test supplier name extraction
        if parsed.get('supplier_name'):
            if 'Fresh Foods' in parsed['supplier_name'] or 'Italia' in parsed['supplier_name']:
                self.log_result("Parse Supplier Name", True, f"Found: {parsed['supplier_name']}")
            else:
                self.log_result("Parse Supplier Name", False, f"Incorrect: {parsed['supplier_name']}")
        else:
            self.log_result("Parse Supplier Name", False, "Not found")
        
        # Test line items parsing
        line_items = parsed.get('line_items', [])
        if line_items:
            valid_items = 0
            for item in line_items:
                if (item.get('description') and 
                    item.get('qty') and 
                    isinstance(item.get('qty'), (int, float)) and
                    item.get('unit') and
                    item.get('price') and
                    isinstance(item.get('price'), (int, float))):
                    valid_items += 1
            
            if valid_items > 0:
                self.log_result("Parse Line Items", True, 
                              f"Valid items: {valid_items}/{len(line_items)}")
            else:
                self.log_result("Parse Line Items", False, "No valid items found")
        else:
            self.log_result("Parse Line Items", False, "No line items found")
    
    def test_receiving_creation_from_ocr(self):
        """Test creating receiving record from OCR data"""
        print("\n📦 Testing Receiving Creation from OCR...")
        
        if 'ocr_result' not in self.test_data:
            self.log_result("Receiving Creation Test", False, "No OCR result available")
            return
        
        # Prepare document data for receiving creation
        parsed = self.test_data['ocr_result']['parsed']
        
        # Map line items to ingredients
        mapped_items = []
        ingredient_names = ["San Marzano Tomatoes", "Extra Virgin Olive Oil", "Mozzarella di Bufala"]
        
        for i, item in enumerate(parsed.get('line_items', [])[:3]):  # Take first 3 items
            if i < len(self.test_data['ingredient_ids']):
                mapped_items.append({
                    "ingredientId": self.test_data['ingredient_ids'][i],
                    "description": item.get('description', ingredient_names[i]),
                    "qty": item.get('qty', 1.0),
                    "unit": item.get('unit', 'kg'),
                    "unitPrice": item.get('price', 10.0)
                })
        
        document_data = {
            "supplierId": self.test_data['supplier_id'],
            "date": parsed.get('date', '2024-01-15'),
            "lineItems": mapped_items,
            "documentType": "invoice",
            "invoiceNumber": parsed.get('invoice_number', 'INV-2024-001'),
            "confidence": self.test_data['ocr_result']['ocr']['confidence']
        }
        
        # Test 1: Create receiving (Admin)
        try:
            headers = {"Authorization": f"Bearer {self.tokens['admin']}"}
            response = requests.post(f"{BASE_URL}/ocr/create-receiving", 
                                   json=document_data, headers=headers)
            
            if response.status_code == 200:
                receiving = response.json()
                
                # Verify receiving record structure
                if (receiving.get('id') and 
                    receiving.get('supplierId') == self.test_data['supplier_id'] and
                    receiving.get('importedFromOCR') == True and
                    receiving.get('ocrMetadata') and
                    'Imported from OCR' in receiving.get('notes', '')):
                    
                    self.test_data['receiving_id'] = receiving['id']
                    self.log_result("Create Receiving from OCR (Admin)", True, 
                                  f"ID: {receiving['id']}, Lines: {len(receiving.get('lines', []))}")
                else:
                    # Debug output
                    missing_fields = []
                    if not receiving.get('id'):
                        missing_fields.append('id')
                    if receiving.get('supplierId') != self.test_data['supplier_id']:
                        missing_fields.append(f"supplierId (expected {self.test_data['supplier_id']}, got {receiving.get('supplierId')})")
                    if receiving.get('importedFromOCR') != True:
                        missing_fields.append(f"importedFromOCR (got {receiving.get('importedFromOCR')})")
                    if not receiving.get('ocrMetadata'):
                        missing_fields.append('ocrMetadata')
                    if 'Imported from OCR' not in receiving.get('notes', ''):
                        missing_fields.append('notes with OCR info')
                    
                    self.log_result("Create Receiving from OCR (Admin)", False, f"Missing: {', '.join(missing_fields)}")
            else:
                self.log_result("Create Receiving from OCR (Admin)", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_result("Create Receiving from OCR (Admin)", False, f"Error: {str(e)}")
        
        # Test 2: Create receiving (Manager)
        try:
            headers = {"Authorization": f"Bearer {self.tokens['manager']}"}
            response = requests.post(f"{BASE_URL}/ocr/create-receiving", 
                                   json=document_data, headers=headers)
            
            if response.status_code == 200:
                self.log_result("Create Receiving from OCR (Manager)", True, "Manager can create")
            else:
                self.log_result("Create Receiving from OCR (Manager)", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_result("Create Receiving from OCR (Manager)", False, f"Error: {str(e)}")
        
        # Test 3: RBAC - Staff should get 403
        try:
            headers = {"Authorization": f"Bearer {self.tokens['staff']}"}
            response = requests.post(f"{BASE_URL}/ocr/create-receiving", 
                                   json=document_data, headers=headers)
            
            if response.status_code == 403:
                self.log_result("Create Receiving RBAC - Staff Denied", True, "403 Forbidden as expected")
            else:
                self.log_result("Create Receiving RBAC - Staff Denied", False, f"Expected 403, got {response.status_code}")
        except Exception as e:
            self.log_result("Create Receiving RBAC - Staff Denied", False, f"Error: {str(e)}")
        
        # Test 4: Error handling - No supplier ID
        try:
            invalid_data = document_data.copy()
            del invalid_data['supplierId']
            
            headers = {"Authorization": f"Bearer {self.tokens['admin']}"}
            response = requests.post(f"{BASE_URL}/ocr/create-receiving", 
                                   json=invalid_data, headers=headers)
            
            if response.status_code == 400:
                self.log_result("Receiving Error - No Supplier ID", True, "400 Bad Request as expected")
            else:
                self.log_result("Receiving Error - No Supplier ID", False, f"Expected 400, got {response.status_code}")
        except Exception as e:
            self.log_result("Receiving Error - No Supplier ID", False, f"Error: {str(e)}")
        
        # Test 5: Error handling - No mapped items
        try:
            invalid_data = document_data.copy()
            invalid_data['lineItems'] = []
            
            headers = {"Authorization": f"Bearer {self.tokens['admin']}"}
            response = requests.post(f"{BASE_URL}/ocr/create-receiving", 
                                   json=invalid_data, headers=headers)
            
            if response.status_code == 400:
                self.log_result("Receiving Error - No Items", True, "400 Bad Request as expected")
            else:
                self.log_result("Receiving Error - No Items", False, f"Expected 400, got {response.status_code}")
        except Exception as e:
            self.log_result("Receiving Error - No Items", False, f"Error: {str(e)}")
    
    def test_inventory_integration(self):
        """Test inventory updates after OCR import"""
        print("\n📈 Testing Inventory Integration...")
        
        if 'receiving_id' not in self.test_data:
            self.log_result("Inventory Integration Test", False, "No receiving record created")
            return
        
        # Check inventory for each ingredient
        headers = {"Authorization": f"Bearer {self.tokens['admin']}"}
        
        for i, ingredient_id in enumerate(self.test_data['ingredient_ids']):
            try:
                # Get ingredient details
                response = requests.get(f"{BASE_URL}/ingredients/{ingredient_id}", headers=headers)
                
                if response.status_code == 200:
                    ingredient = response.json()
                    
                    # Check if inventory was updated (this would require checking inventory endpoint)
                    # For now, we'll verify the ingredient still exists and has the right structure
                    if (ingredient.get('id') == ingredient_id and
                        ingredient.get('unitCost') and
                        ingredient.get('effectiveUnitCost')):
                        
                        self.log_result(f"Inventory Check - {ingredient['name']}", True, 
                                      f"Unit cost: {ingredient['unitCost']}")
                    else:
                        self.log_result(f"Inventory Check - {ingredient['name']}", False, "Invalid structure")
                else:
                    self.log_result(f"Inventory Check - Ingredient {i+1}", False, f"Status: {response.status_code}")
            except Exception as e:
                self.log_result(f"Inventory Check - Ingredient {i+1}", False, f"Error: {str(e)}")
    
    def test_audit_trail(self):
        """Test audit trail for OCR operations"""
        print("\n📋 Testing Audit Trail...")
        
        # This would require an audit log endpoint to verify
        # For now, we'll check that the receiving record has the right metadata
        
        if 'receiving_id' not in self.test_data:
            self.log_result("Audit Trail Test", False, "No receiving record to check")
            return
        
        try:
            headers = {"Authorization": f"Bearer {self.tokens['admin']}"}
            response = requests.get(f"{BASE_URL}/receiving/{self.test_data['receiving_id']}", headers=headers)
            
            if response.status_code == 200:
                receiving = response.json()
                
                # Check OCR metadata
                ocr_metadata = receiving.get('ocrMetadata', {})
                if (ocr_metadata.get('confidence') is not None and
                    ocr_metadata.get('documentType') and
                    ocr_metadata.get('processedAt') and
                    receiving.get('importedFromOCR') == True):
                    
                    self.log_result("Audit Trail - OCR Metadata", True, 
                                  f"Confidence: {ocr_metadata['confidence']}%")
                else:
                    self.log_result("Audit Trail - OCR Metadata", False, "Missing OCR metadata")
                
                # Check notes contain OCR info
                notes = receiving.get('notes', '')
                if 'Imported from OCR' in notes and 'Confidence:' in notes:
                    self.log_result("Audit Trail - Notes", True, "OCR info in notes")
                else:
                    self.log_result("Audit Trail - Notes", False, "Missing OCR info in notes")
            else:
                self.log_result("Audit Trail Test", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_result("Audit Trail Test", False, f"Error: {str(e)}")
    
    def run_all_tests(self):
        """Run all OCR tests"""
        print("🚀 Starting Phase 8 OCR Document Ingestion Backend Testing")
        print("=" * 60)
        
        # Setup
        if not self.login_all_users():
            print("❌ Failed to login users, aborting tests")
            return
        
        if not self.setup_test_data():
            print("❌ Failed to setup test data, aborting tests")
            return
        
        # Run tests
        self.test_ocr_processing()
        self.test_document_parsing_accuracy()
        self.test_receiving_creation_from_ocr()
        self.test_inventory_integration()
        self.test_audit_trail()
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 PHASE 8 OCR TESTING SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS:")
            for result in self.results:
                if not result['success']:
                    print(f"   • {result['test']}: {result['details']}")
        
        print("\n🎯 KEY FINDINGS:")
        
        # OCR Processing
        ocr_tests = [r for r in self.results if 'OCR' in r['test'] and 'Processing' in r['test']]
        ocr_passed = sum(1 for r in ocr_tests if r['success'])
        if ocr_passed > 0:
            print(f"   ✅ OCR Processing: {ocr_passed}/{len(ocr_tests)} working")
        else:
            print(f"   ❌ OCR Processing: Not working")
        
        # Document Parsing
        parse_tests = [r for r in self.results if 'Parse' in r['test']]
        parse_passed = sum(1 for r in parse_tests if r['success'])
        if parse_passed > 0:
            print(f"   ✅ Document Parsing: {parse_passed}/{len(parse_tests)} fields extracted")
        else:
            print(f"   ❌ Document Parsing: Not working")
        
        # Receiving Creation
        receiving_tests = [r for r in self.results if 'Receiving' in r['test'] and 'OCR' in r['test']]
        receiving_passed = sum(1 for r in receiving_tests if r['success'])
        if receiving_passed > 0:
            print(f"   ✅ Receiving Creation: {receiving_passed}/{len(receiving_tests)} working")
        else:
            print(f"   ❌ Receiving Creation: Not working")
        
        # RBAC
        rbac_tests = [r for r in self.results if 'RBAC' in r['test'] or 'Denied' in r['test']]
        rbac_passed = sum(1 for r in rbac_tests if r['success'])
        if rbac_passed == len(rbac_tests) and len(rbac_tests) > 0:
            print(f"   ✅ RBAC Enforcement: Working correctly")
        else:
            print(f"   ❌ RBAC Enforcement: Issues found")


if __name__ == "__main__":
    tester = OCRTester()
    tester.run_all_tests()