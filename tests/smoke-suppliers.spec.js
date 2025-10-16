/**
 * Suppliers Module - Smoke Test Suite
 * Fast regression tests for core Suppliers functionality
 * 
 * Tests:
 * 1. Create supplier → attach file → download → detach → delete
 * 2. File validation (>10MB, disallowed MIME)
 * 3. RBAC (staff vs admin permissions)
 * 4. i18n toggle (EN ↔ IT)
 */

const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'https://ristobrain.preview.emergentagent.com';
const API = `${BACKEND_URL}/api`;

// Test credentials
const ADMIN_CREDS = { email: 'admin@test.com', password: 'password123' };
const STAFF_CREDS = { email: 'staff@test.com', password: 'password123' };

// Helper: Login and return token
async function login(page, email, password) {
  await page.goto('/login');
  await page.fill('input[type="email"]', email);
  await page.fill('input[type="password"]', password);
  await page.click('button[type="submit"]');
  await page.waitForLoadState('networkidle');
  
  // Get token from localStorage
  const token = await page.evaluate(() => localStorage.getItem('token'));
  return token;
}

// Helper: Create test file
function createTestFile(name, sizeInMB, content = 'test content') {
  const filePath = path.join(__dirname, name);
  const buffer = Buffer.alloc(sizeInMB * 1024 * 1024, content);
  fs.writeFileSync(filePath, buffer);
  return filePath;
}

test.describe('Suppliers Module - Smoke Tests', () => {
  
  test('1. Full supplier lifecycle: create → attach file → download → detach → delete', async ({ page }) => {
    // Login as admin
    await login(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
    
    // Navigate to Suppliers
    await page.goto('/suppliers');
    await page.waitForLoadState('networkidle');
    
    // Create supplier
    await page.click('text=Add Supplier');
    await page.fill('input#name', 'Test Smoke Supplier');
    await page.fill('input#contactName', 'John Doe');
    await page.fill('input#contactPhone', '+1234567890');
    await page.fill('input#contactEmail', 'john@test.com');
    await page.fill('textarea#notes', 'Test supplier for smoke tests');
    await page.click('button:has-text("Create")');
    
    // Wait for success toast
    await page.waitForSelector('text=Supplier created successfully', { timeout: 5000 });
    
    // Verify supplier appears in list
    await expect(page.locator('text=Test Smoke Supplier')).toBeVisible();
    
    // Attach file (create a small test PDF)
    const testFilePath = createTestFile('test-smoke.pdf', 0.5); // 500KB
    
    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles(testFilePath);
    
    // Wait for upload success
    await page.waitForSelector('text=File uploaded successfully', { timeout: 10000 });
    
    // Verify file appears in list
    await expect(page.locator('text=test-smoke.pdf')).toBeVisible();
    
    // Download file (verify download triggers)
    const downloadPromise = page.waitForEvent('download');
    await page.click('button:has-text("Download"):visible', { first: true });
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toContain('.pdf');
    
    // Detach file
    await page.click('button[title*="delete"]:visible >> nth=0');
    await page.waitForSelector('text=File deleted', { timeout: 5000 });
    
    // Verify file removed
    await expect(page.locator('text=test-smoke.pdf')).not.toBeVisible();
    
    // Delete supplier
    await page.click('button:has-text("Delete"):visible >> nth=0');
    await page.waitForSelector('text=Supplier deleted', { timeout: 5000 });
    
    // Verify supplier removed
    await expect(page.locator('text=Test Smoke Supplier')).not.toBeVisible();
    
    // Cleanup
    fs.unlinkSync(testFilePath);
  });

  test('2. File validation: reject >10MB file', async ({ page }) => {
    // Login as admin
    await login(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
    
    // Create a supplier first
    await page.goto('/suppliers');
    await page.click('text=Add Supplier');
    await page.fill('input#name', 'Test Validation Supplier');
    await page.click('button:has-text("Create")');
    await page.waitForSelector('text=Supplier created successfully');
    
    // Try to upload a >10MB file
    const largeFilePath = createTestFile('large-test.pdf', 11); // 11MB
    
    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles(largeFilePath);
    
    // Wait for error message
    await page.waitForSelector('text=File too large', { timeout: 5000 });
    
    // Cleanup supplier and file
    await page.click('button:has-text("Delete"):visible >> nth=0');
    await page.waitForSelector('text=Supplier deleted');
    fs.unlinkSync(largeFilePath);
  });

  test('3. File validation: reject disallowed MIME type', async ({ page }) => {
    // Login as admin
    await login(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
    
    // Create a supplier
    await page.goto('/suppliers');
    await page.click('text=Add Supplier');
    await page.fill('input#name', 'Test MIME Supplier');
    await page.click('button:has-text("Create")');
    await page.waitForSelector('text=Supplier created successfully');
    
    // Create a text file (disallowed MIME type)
    const txtFilePath = path.join(__dirname, 'test.txt');
    fs.writeFileSync(txtFilePath, 'This is a plain text file');
    
    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles(txtFilePath);
    
    // Wait for error message about file type
    await page.waitForSelector('text=/File type not allowed|Failed to upload/', { timeout: 5000 });
    
    // Cleanup
    await page.click('button:has-text("Delete"):visible >> nth=0');
    await page.waitForSelector('text=Supplier deleted');
    fs.unlinkSync(txtFilePath);
  });

  test('4. RBAC: staff cannot delete supplier', async ({ page }) => {
    // First, create supplier as admin
    await login(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
    await page.goto('/suppliers');
    await page.click('text=Add Supplier');
    await page.fill('input#name', 'Test RBAC Supplier');
    await page.click('button:has-text("Create")');
    await page.waitForSelector('text=Supplier created successfully');
    
    // Logout and login as staff
    await page.click('[data-testid="logout-button"]');
    await login(page, STAFF_CREDS.email, STAFF_CREDS.password);
    
    // Navigate to Suppliers
    await page.goto('/suppliers');
    
    // Try to delete supplier
    await page.click('button:has-text("Delete"):visible >> nth=0');
    
    // Should see permission error or button disabled
    // (This will depend on actual RBAC implementation)
    const errorVisible = await page.locator('text=/permission|forbidden|not allowed/i').isVisible({ timeout: 3000 }).catch(() => false);
    
    // If no error, verify supplier still exists (delete didn't work)
    if (!errorVisible) {
      await page.reload();
      await expect(page.locator('text=Test RBAC Supplier')).toBeVisible();
    }
    
    // Cleanup: login as admin and delete
    await page.click('[data-testid="logout-button"]');
    await login(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
    await page.goto('/suppliers');
    await page.click('button:has-text("Delete"):visible >> nth=0');
    await page.waitForSelector('text=Supplier deleted');
  });

  test('5. i18n: EN ↔ IT toggle reflects in Suppliers UI', async ({ page }) => {
    // Login as admin
    await login(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
    
    // Navigate to Suppliers
    await page.goto('/suppliers');
    await page.waitForLoadState('networkidle');
    
    // Check English labels
    await expect(page.locator('h1:has-text("Suppliers")')).toBeVisible();
    await expect(page.locator('text=Add Supplier')).toBeVisible();
    
    // Switch to Italian
    await page.goto('/settings');
    await page.selectOption('select#locale', { value: 'it-IT' });
    await page.click('button:has-text("Save")');
    await page.waitForSelector('text=/salvato|aggiornato/i', { timeout: 5000 });
    
    // Navigate back to Suppliers
    await page.goto('/suppliers');
    await page.waitForLoadState('networkidle');
    
    // Check Italian labels
    await expect(page.locator('h1:has-text("Fornitori")')).toBeVisible();
    await expect(page.locator('text=Aggiungi Fornitore')).toBeVisible();
    
    // Switch back to English
    await page.goto('/settings');
    await page.selectOption('select#locale', { value: 'en-US' });
    await page.click('button:has-text("Salva")'); // Button still in Italian
    await page.waitForSelector('text=/saved|updated/i', { timeout: 5000 });
    
    // Verify English restored
    await page.goto('/suppliers');
    await expect(page.locator('h1:has-text("Suppliers")')).toBeVisible();
  });
});
