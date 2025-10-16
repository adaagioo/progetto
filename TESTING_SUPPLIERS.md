# Suppliers Module - Testing Guide

## Overview
Comprehensive testing suite for the Suppliers module, including CRUD operations, file attachments, validation, RBAC, and i18n.

## Backend Testing (Completed ✅)
All backend endpoints have been tested and verified:
- **23/23 tests passed** (100% success rate)
- Storage service with MIME validation and SHA256 hashing
- File upload/download/delete endpoints
- Suppliers CRUD operations
- File attachments to suppliers
- Audit logging
- Tenant isolation and security

## Frontend Smoke Tests

### Prerequisites
```bash
# Install Playwright (if not already installed)
cd /app/frontend
yarn add -D @playwright/test
npx playwright install
```

### Running Smoke Tests

**Headless mode (CI/CD):**
```bash
cd /app/frontend
yarn test:smoke
```

**Headed mode (debugging):**
```bash
cd /app/frontend
yarn test:smoke:headed
```

### Test Coverage

#### 1. Full Supplier Lifecycle
- Create supplier with all fields
- Attach PDF file (validated)
- Download file
- Detach file
- Delete supplier

#### 2. File Validation - Size Limit
- Attempt to upload >10MB file
- Verify rejection with error message

#### 3. File Validation - MIME Type
- Attempt to upload disallowed file type (.txt)
- Verify rejection with error message

#### 4. RBAC - Permission Enforcement
- Staff user attempts to delete supplier
- Verify operation is blocked or fails
- Admin can successfully delete

#### 5. i18n - Language Toggle
- Verify English labels (Suppliers, Add Supplier)
- Switch to Italian via Settings
- Verify Italian labels (Fornitori, Aggiungi Fornitore)
- Switch back to English
- Verify labels restored

### Test Files Location
- `/app/tests/smoke-suppliers.spec.js` - Playwright smoke tests
- `/app/test_result.md` - Detailed test results and status

### Manual UAT Checklist
What to verify during manual testing:

#### ✅ CRUD Operations
- [ ] Create supplier with full fields (name, contact, notes)
- [ ] Create supplier with minimal fields (name only)
- [ ] List suppliers (restaurant-scoped)
- [ ] View supplier details
- [ ] Update supplier information
- [ ] Delete supplier and verify removal

#### ✅ File Operations
- [ ] Upload PDF file (<10MB)
- [ ] Upload XLSX/XLS file
- [ ] Upload CSV file
- [ ] Upload DOCX/DOC file
- [ ] Upload JPG/PNG image
- [ ] Download file and verify content
- [ ] Detach file from supplier
- [ ] Verify file removed from storage

#### ✅ Validation
- [ ] Upload >10MB file → error message displayed
- [ ] Upload .txt file → error message displayed
- [ ] Create supplier without name → validation error
- [ ] Proper error messages for all failures

#### ✅ Security
- [ ] Files served via authenticated route only
- [ ] Download headers include Content-Type and Content-Disposition
- [ ] Cannot access another restaurant's suppliers
- [ ] Cannot access another restaurant's files

#### ✅ Audit Logging
- [ ] Supplier creation logged
- [ ] Supplier update logged
- [ ] Supplier deletion logged
- [ ] File upload logged
- [ ] File attachment logged
- [ ] File detachment logged

#### ✅ RBAC
- [ ] Staff user cannot delete supplier
- [ ] Staff user cannot delete files
- [ ] Admin can perform all operations
- [ ] Proper error messages for forbidden actions

#### ✅ Localization
- [ ] All labels in English when locale is en-US
- [ ] All labels in Italian when locale is it-IT
- [ ] Toasts and messages localized
- [ ] Form validation messages localized
- [ ] Navigation link localized

#### ✅ UI/UX
- [ ] Responsive design works on mobile/tablet/desktop
- [ ] File upload progress indication
- [ ] Loading states during operations
- [ ] Success/error toasts display correctly
- [ ] Confirmation dialogs for destructive actions

### Known Limitations
- OCR/parsing is stubbed (placeholder for future implementation)
- RBAC implementation may need refinement based on permission matrix
- File chunking not yet implemented for large files

### Next Steps
After successful UAT:
1. Proceed with Receiving module implementation
2. Implement Inventory Valuation with weighted average costing
3. Enhance Dashboard with clickable monetary cards

### Support
For issues or questions:
- Check `/app/test_result.md` for detailed test status
- Review backend logs: `tail -f /var/log/supervisor/backend.err.log`
- Review frontend logs in browser console
- Audit logs available via: `GET /api/audit-logs` (if endpoint added)
