#!/usr/bin/env python3
"""
RistoBrain Backend API Test Suite
Tests health endpoints, authentication, and basic restaurant functionality
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any


class RistoBrainAPITester:
    def __init__(self, base_url: str = "https://9fe87d15-e7b1-434d-a9bd-c6f09d038635.preview.emergentagent.com"):
        self.base_url = base_url.rstrip('/')
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.session = requests.Session()
        self.session.timeout = 30
        
        # Test credentials
        self.admin_email = "admin@ristobrain.app"
        self.admin_password = "ChangeMe123!"

    def log(self, message: str, level: str = "INFO"):
        """Log test messages"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def run_test(self, name: str, method: str, endpoint: str, expected_status: int = 200, 
                 data: Dict[Any, Any] = None, headers: Dict[str, str] = None) -> tuple[bool, dict]:
        """Execute a single API test"""
        url = f"{self.base_url}/api/{endpoint.lstrip('/')}"
        
        # Default headers
        request_headers = {'Content-Type': 'application/json'}
        if self.token:
            request_headers['Authorization'] = f'Bearer {self.token}'
        
        # Add custom headers
        if headers:
            request_headers.update(headers)

        self.tests_run += 1
        self.log(f"Testing {name}...")
        self.log(f"  URL: {url}")
        
        try:
            # Make request
            if method == 'GET':
                response = self.session.get(url, headers=request_headers)
            elif method == 'POST':
                response = self.session.post(url, json=data, headers=request_headers)
            elif method == 'PUT':
                response = self.session.put(url, json=data, headers=request_headers)
            elif method == 'DELETE':
                response = self.session.delete(url, headers=request_headers)
            else:
                raise ValueError(f"Unsupported method: {method}")

            # Check status code
            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                self.log(f"  ✅ PASSED - Status: {response.status_code}")
            else:
                self.log(f"  ❌ FAILED - Expected {expected_status}, got {response.status_code}")
                self.log(f"  Response: {response.text[:200]}...")

            # Try to parse JSON response
            try:
                response_data = response.json()
            except:
                response_data = {"raw_response": response.text}

            return success, response_data

        except Exception as e:
            self.log(f"  ❌ FAILED - Error: {str(e)}", "ERROR")
            return False, {"error": str(e)}

    def test_health_endpoints(self) -> bool:
        """Test health check endpoints"""
        self.log("=== Testing Health Endpoints ===")
        
        # Test liveness endpoint
        success1, _ = self.run_test(
            "Liveness Probe",
            "GET", 
            "health/live",
            200
        )
        
        # Test readiness endpoint  
        success2, response = self.run_test(
            "Readiness Probe",
            "GET",
            "health/ready", 
            200
        )
        
        # Verify readiness response structure
        if success2 and isinstance(response, dict):
            has_ok = response.get("ok") == True
            has_db = response.get("db") == "ok"
            if not (has_ok and has_db):
                self.log(f"  ⚠️  WARNING - Readiness response missing expected fields: {response}")
                success2 = False
        
        return success1 and success2

    def test_authentication(self) -> bool:
        """Test authentication with super admin credentials"""
        self.log("=== Testing Authentication ===")
        
        # Test login
        success, response = self.run_test(
            "Super Admin Login",
            "POST",
            "auth/login",
            200,
            data={
                "email": self.admin_email,
                "password": self.admin_password
            }
        )
        
        if success and isinstance(response, dict):
            # Extract token
            token = response.get("access_token")
            if token:
                self.token = token
                self.log(f"  🔐 Token acquired: {token[:20]}...")
                
                # Test /auth/me endpoint
                me_success, me_response = self.run_test(
                    "Get Current User",
                    "GET",
                    "auth/me",
                    200
                )
                
                if me_success:
                    self.log(f"  👤 User info: {me_response.get('email', 'N/A')}")
                
                return True
            else:
                self.log("  ❌ No access_token in response", "ERROR")
                return False
        
        return False

    def test_restaurant_endpoint(self) -> bool:
        """Test restaurant data endpoint"""
        self.log("=== Testing Restaurant Endpoint ===")
        
        if not self.token:
            self.log("  ⚠️  Skipping - No authentication token", "WARN")
            return False
            
        success, response = self.run_test(
            "Get Restaurant Data",
            "GET",
            "restaurant",
            200
        )
        
        return success

    def test_ingredients_endpoint(self) -> bool:
        """Test ingredients list endpoint"""
        self.log("=== Testing Ingredients Endpoint ===")
        
        if not self.token:
            self.log("  ⚠️  Skipping - No authentication token", "WARN")
            return False
            
        success, response = self.run_test(
            "Get Ingredients List",
            "GET", 
            "ingredients",
            200
        )
        
        return success

    def run_all_tests(self) -> dict:
        """Execute all backend tests"""
        self.log("🚀 Starting RistoBrain Backend API Tests")
        self.log(f"Base URL: {self.base_url}")
        
        test_results = {
            "health_endpoints": self.test_health_endpoints(),
            "authentication": self.test_authentication(),
            "restaurant_endpoint": self.test_restaurant_endpoint(),
            "ingredients_endpoint": self.test_ingredients_endpoint()
        }
        
        # Summary
        self.log("=" * 50)
        self.log(f"📊 BACKEND TEST RESULTS:")
        self.log(f"   Tests Run: {self.tests_run}")
        self.log(f"   Tests Passed: {self.tests_passed}")
        self.log(f"   Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        # Individual test results
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            self.log(f"   {test_name}: {status}")
        
        return test_results


def main():
    """Main test execution"""
    tester = RistoBrainAPITester()
    results = tester.run_all_tests()
    
    # Exit with error code if any tests failed
    all_passed = all(results.values())
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())