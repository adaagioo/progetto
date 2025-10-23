# RistoBrain Phase 6 (Suppliers+) - UAT Package

## 🎯 Release Overview
**Feature**: Suppliers+ with Receiving UI Enhancements
**Version**: Phase 6 Complete
**Date**: October 19, 2025

## 📋 What's New

### Phase 6 Features
- **Supplier Mapping**: Preferred supplier selection for ingredients
- **Price History**: Historical price tracking from receiving records
- **Price List Management**: Upload, categorize, and download supplier price lists
- **Auto-fill Intelligence**: Automatic supplier and price population in receiving
- **Enhanced Receiving UI**: Price history popover, price list viewer, improved UX

---

## 🌐 Staging Environment

### URLs
- **Application**: https://bulk-delete-rbac.preview.emergentagent.com
- **API Base**: https://bulk-delete-rbac.preview.emergentagent.com/api

### Test Credentials

| Role    | Email                | Password    | Access Level                          |
|---------|----------------------|-------------|---------------------------------------|
| Admin   | admin@test.com       | admin123    | Full access (CRUD, Users, Settings)   |
| Manager | manager@test.com     | manager123  | CRUD access (no Users management)     |
| Staff   | staff@test.com       | staff123    | Read-only access                      |

---

## 🧪 UAT Test Scenarios

### 1. Supplier Management - Price Lists

**Test**: Upload Price List to Supplier
1. Login as Admin
2. Navigate to **Suppliers** page
3. Create or select existing supplier
4. Click "Upload File" button
5. Select file and choose "Price List" as file type
6. Upload
7. **Expected**: File uploaded with green "Price List" badge
8. **Expected**: File visible in supplier card with download link

**Test**: Download Price List
1. Find supplier with price list file
2. Click download icon next to price list
3. **Expected**: File downloads successfully

### 2. Ingredient Management - Preferred Supplier

**Test**: Set Preferred Supplier for Ingredient
1. Navigate to **Ingredients** page
2. Create or edit an ingredient
3. In the form, find "Preferred Supplier" dropdown
4. Select a supplier
5. Save
6. **Expected**: Ingredient card shows preferred supplier name (if populated)
7. **Expected**: Ingredient saved with supplier mapping

**Test**: View Ingredient with Preferred Supplier
1. Navigate to Ingredients page
2. Find ingredient with preferred supplier
3. **Expected**: Ingredient details show supplier information

### 3. Receiving - Auto-fill Intelligence

**Test**: Supplier Auto-fill from Ingredient
1. Navigate to **Receiving** ("Ricevute" in IT) page
2. Click "Add Receiving"
3. In Line Items section, select an ingredient dropdown
4. Choose an ingredient that has a preferred supplier
5. **Expected**: Supplier dropdown auto-fills with preferred supplier
6. **Expected**: Toast notification appears: "Supplier auto-filled from ingredient"
7. **Expected**: Unit price auto-fills from ingredient's last price
8. **Expected**: Pack format auto-fills from ingredient's pack size

**Test**: Manual Override
1. In same form, manually change the supplier dropdown
2. **Expected**: User can override the auto-filled supplier
3. Add another line item
4. Select different ingredient
5. **Expected**: Supplier remains the manually selected one (no override)

### 4. Receiving - Price History Popover

**Test**: View Price History
1. In Receiving form, add a line item
2. Select an ingredient that has been received before
3. Look at "Price" field label
4. **Expected**: Small history icon (clock) appears next to "Price" label
5. Click the history icon
6. **Expected**: Popover opens showing price history
7. **Expected**: Shows last 5 receiving entries:
   - Date of receiving
   - Unit price (formatted with currency)
   - Quantity and unit
   - Pack format
   - Supplier name
8. **Expected**: History sorted newest first
9. **Expected**: Loading state appears briefly

**Test**: No History Available
1. Select an ingredient that has never been received
2. Click history icon
3. **Expected**: "No price history available" message shown

### 5. Receiving - Price List Viewer

**Test**: View Supplier Price Lists in Receiving
1. In Receiving form, select a supplier that has price lists
2. **Expected**: Blue info box appears below supplier selection
3. **Expected**: Box shows "Price Lists" header
4. **Expected**: Lists all price list files for that supplier
5. **Expected**: Each file has download link
6. Click download link
7. **Expected**: Price list file downloads

**Test**: No Price Lists
1. Select a supplier without price lists
2. **Expected**: No price list section appears (clean UI)

### 6. Language Switching - Receiving i18n

**Test**: Switch to Italian
1. Go to Settings → Language & Currency
2. Select "Italiano (IT)"
3. Navigate to Receiving page
4. **Expected**: All labels translated:
   - "Ricevute" (Receiving)
   - "Fornitore" (Supplier)
   - "Categoria" (Category)
   - "Articoli" (Line Items)
   - "Prezzo Unitario" (Unit Price)
   - "Storico Prezzi" (Price History)
   - "Liste Prezzi" (Price Lists)

**Test**: Switch back to English
1. Go to Settings
2. Select "English (EN)"
3. **Expected**: All labels back to English

### 7. RBAC - Receiving Permissions

**Test**: Staff Read-Only
1. Logout
2. Login as Staff (staff@test.com / staff123)
3. Navigate to Receiving
4. **Expected**: Can view existing receiving records
5. Try to click "Add Receiving"
6. **Expected**: Button not visible OR disabled
7. Try to edit existing receiving
8. **Expected**: Edit button not visible OR disabled

**Test**: Manager Full Access
1. Logout
2. Login as Manager (manager@test.com / manager123)
3. Navigate to Receiving
4. **Expected**: "Add Receiving" button visible
5. Create new receiving record
6. **Expected**: Successfully created
7. Edit existing receiving
8. **Expected**: Successfully updated
9. Delete receiving
10. **Expected**: Successfully deleted

### 8. Currency & Locale - Price Formatting

**Test**: Price Display
1. Ensure language set to English, currency to EUR
2. View receiving records
3. **Expected**: Prices formatted as €XX.XX
4. View price history popover
5. **Expected**: Historical prices formatted with € symbol

**Test**: Switch Currency
1. Go to Settings → Language & Currency
2. Switch to USD
3. Navigate to Receiving
4. **Expected**: All prices formatted as $XX.XX
5. **Expected**: Price history shows $ symbol

---

## 📊 Seeded Test Data

**Note**: Phase 6 uses existing production data from previous phases. If starting fresh, run seed scripts:

```bash
cd /app/backend
python seed_phase4_uat.py  # Creates suppliers, ingredients, recipes
```

### Expected Data After Seeding
- **3 Suppliers**: Metro Cash & Carry, Sysco Italia, Chef Store
- **10+ Ingredients**: With preferred suppliers assigned
- **Receiving Records**: Historical data for price history testing
- **Price Lists**: Uploaded to suppliers for download testing

---

## ✅ Acceptance Criteria

### Must Pass
- [ ] Ingredient can be assigned preferred supplier
- [ ] Preferred supplier auto-fills in receiving when ingredient selected
- [ ] Last price auto-fills in receiving
- [ ] Price history popover shows historical prices (sorted newest first)
- [ ] Price history includes supplier names, dates, quantities
- [ ] Price lists can be uploaded to suppliers with "price_list" type
- [ ] Price lists visible and downloadable in receiving form
- [ ] All prices formatted with correct currency symbol (EUR/USD)
- [ ] Language switching updates all receiving labels (EN/IT)
- [ ] RBAC: Staff cannot create/edit receiving
- [ ] RBAC: Admin/Manager can create/edit/delete receiving
- [ ] Toast notifications appear for auto-fill actions

### Nice to Have
- [ ] Price history shows trend (up/down indicators)
- [ ] Price list preview (without download)
- [ ] Pack rounding tooltip in receiving
- [ ] Supplier notes visible in receiving form

---

## 🔧 Technical Details

### Backend Endpoints Added
- `GET /api/ingredients/{id}/price-history?limit=10` - Get price history
- Enhanced `POST /api/suppliers/files` - Supports fileType parameter
- RBAC checks added to receiving endpoints (create/update/delete)

### Frontend Components Updated
- **Receiving.js**: Price history popover, price list viewer, auto-fill logic
- **Ingredients.js**: Preferred supplier dropdown
- **Suppliers.js**: Price list upload with fileType

### Data Models
```json
{
  "ingredient": {
    "preferredSupplierId": "uuid",
    "preferredSupplierName": "Metro Cash & Carry"
  },
  "supplier": {
    "files": [{
      "id": "uuid",
      "filename": "price_list_oct_2025.pdf",
      "fileType": "price_list",
      "downloadUrl": "https://..."
    }]
  },
  "priceHistory": {
    "ingredientId": "uuid",
    "ingredientName": "San Marzano Tomatoes",
    "history": [{
      "date": "2025-10-15",
      "unitPrice": 3.40,
      "qty": 10.0,
      "unit": "kg",
      "packFormat": "2.5 kg",
      "supplierId": "uuid",
      "supplierName": "Metro Cash & Carry"
    }]
  }
}
```

---

## 🐛 Known Issues

None at this time. All Phase 6 functionality is working as expected.

---

## 📞 Support

For issues during UAT:
1. Check browser console for errors (F12)
2. Verify you're using correct credentials
3. Ensure test data is seeded
4. Try clearing browser cache and reloading
5. Test in incognito mode to rule out browser extensions

---

## 🚀 Next Phases

After Phase 6 approval:
1. **Phase 8 (Priority)**: Document Ingestion / OCR
   - Tesseract MVP for invoice parsing
   - Review & Mapping UI
   - Receiving integration
   - Audit trail

2. **Phase 7**: RBAC Matrix
   - Customizable permissions
   - Admin-only matrix UI
   - Immediate enforcement

---

## 📝 Test Results Template

Please fill this out during UAT:

| Test Scenario | Status | Notes |
|---------------|--------|-------|
| Upload price list to supplier | ⬜ Pass / ❌ Fail | |
| Download price list | ⬜ Pass / ❌ Fail | |
| Set preferred supplier | ⬜ Pass / ❌ Fail | |
| Supplier auto-fill in receiving | ⬜ Pass / ❌ Fail | |
| Price auto-fill in receiving | ⬜ Pass / ❌ Fail | |
| View price history popover | ⬜ Pass / ❌ Fail | |
| No history message | ⬜ Pass / ❌ Fail | |
| View price lists in receiving | ⬜ Pass / ❌ Fail | |
| Download from receiving | ⬜ Pass / ❌ Fail | |
| Switch to Italian | ⬜ Pass / ❌ Fail | |
| Receiving labels in Italian | ⬜ Pass / ❌ Fail | |
| Staff read-only access | ⬜ Pass / ❌ Fail | |
| Manager full access | ⬜ Pass / ❌ Fail | |
| EUR currency formatting | ⬜ Pass / ❌ Fail | |
| USD currency formatting | ⬜ Pass / ❌ Fail | |

**Overall UAT Result**: ⬜ Approved / ❌ Rejected

**Tester Name**: ____________________
**Date**: ____________________
**Additional Comments**:
