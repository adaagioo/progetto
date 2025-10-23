# RistoBrain Allergen Taxonomy - UAT Package

## 🎯 Release Overview
**Feature**: Allergen Taxonomy Integration with EU-14 Compliance
**Version**: Phase P0 Complete
**Date**: October 19, 2025

## 📋 What's New

### Allergen Management System
- **Fixed Checklist**: 12 EU-14 standard allergens (GLUTEN, CRUSTACEANS, MOLLUSCS, EGGS, FISH, TREE_NUTS, SOY, DAIRY, SESAME, CELERY, MUSTARD, SULPHITES)
- **Custom Allergens**: Free-text "Other/Altro" field for non-standard allergens
- **Allergen Propagation**: Automatic aggregation from Ingredients → Preparations → Recipes
- **Bilingual Support**: Complete EN/IT translations for all allergen labels

### User Interface Enhancements
- **Search & Filter**: Search by name + filter by allergen on Ingredients and Recipes pages
- **Allergen Badges**: Visual indicators with localized labels (red for standard, orange for custom)
- **AllergenSelector Component**: Consistent allergen input across all forms

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

### 1. Ingredients Page - Allergen Management

**Test**: Create Ingredient with Standard Allergens
1. Login as Admin
2. Navigate to **Ingredients** page
3. Click "Add Ingredient"
4. Fill in:
   - Name: "Test Flour"
   - Pack Size: 25 kg
   - Pack Cost: €15.00
   - Select allergens: ✅ GLUTEN
5. Save
6. **Expected**: Ingredient card shows red badge "gluten" (EN) or "glutine" (IT)

**Test**: Create Ingredient with Custom Allergens
1. Create new ingredient "Special Oil"
2. Don't select any standard allergens
3. In "Other Allergens" field, type "truffle extract" and click Add
4. Add another: "special seasoning"
5. Save
6. **Expected**: Ingredient card shows 2 orange badges with custom allergen names

**Test**: Search and Filter
1. Use search bar: type "flour"
2. **Expected**: Only flour ingredients shown
3. Clear search
4. Use allergen filter dropdown: select "gluten"
5. **Expected**: Only ingredients with GLUTEN allergen shown
6. **Expected**: Filter dropdown shows allergen names in current language

### 2. Preparations Page - Allergen Propagation

**Test**: Verify Automatic Allergen Propagation
1. Navigate to **Preparations** page
2. Find "Fresh Pasta Dough" (pre-seeded)
3. **Expected**: Shows allergen badges for "EGGS" and "GLUTEN"
4. **Expected**: These allergens come from flour (GLUTEN) + eggs (EGGS) ingredients
5. Click to view details
6. **Expected**: Allergens displayed with localized labels

### 3. Recipes Page - Allergen Aggregation

**Test**: Complex Allergen Aggregation
1. Navigate to **Recipes** page
2. Find "Truffle Pasta with Nuts" (pre-seeded)
3. **Expected**: Shows allergen badges:
   - Standard: EGGS, GLUTEN, TREE_NUTS
   - Custom: White Truffle Extract, Artificial Truffle Flavoring
4. **Expected**: Standard allergens in red, custom in orange

**Test**: Search and Filter Recipes
1. Use search bar: type "pasta"
2. **Expected**: Only pasta recipes shown
3. Use allergen filter: select "GLUTEN"
4. **Expected**: Only recipes containing gluten shown
5. **Expected**: Filters work alongside search

### 4. Language Switching - i18n Verification

**Test**: Switch to Italian
1. Click Settings (gear icon)
2. Navigate to "Language & Currency" tab
3. Select "Italiano (IT)"
4. **Expected**: All UI text switches to Italian
5. Navigate to Ingredients page
6. **Expected**: Allergen badges show Italian labels:
   - gluten → glutine
   - dairy → latticini
   - tree nuts → frutta a guscio
   - eggs → uova
7. **Expected**: Filter dropdown shows Italian allergen names
8. **Expected**: "Other Allergens" → "Altri Allergeni"

**Test**: Switch back to English
1. Go to Settings
2. Select "English (EN)"
3. **Expected**: All labels back to English

### 5. RBAC Verification

**Test**: Staff Read-Only Access
1. Logout
2. Login as Staff (staff@test.com / staff123)
3. Navigate to Ingredients
4. **Expected**: NO "Add Ingredient" button visible
5. Click Edit on any ingredient
6. **Expected**: Can view but cannot save changes (or edit button not visible)

**Test**: Manager Edit Access
1. Logout
2. Login as Manager (manager@test.com / manager123)
3. Navigate to Ingredients
4. **Expected**: "Add Ingredient" button visible
5. Create or edit an ingredient
6. **Expected**: Can successfully save changes

---

## 📊 Seeded Test Data

### Ingredients (10 items with diverse allergens)
1. **All-Purpose Flour** - GLUTEN
2. **Fresh Milk** - DAIRY
3. **Shrimp (Fresh)** - CRUSTACEANS
4. **Mixed Nuts** - TREE_NUTS
5. **Eggs (Free Range)** - EGGS
6. **White Truffle Oil** - Custom: "White Truffle Extract", "Artificial Truffle Flavoring"
7. **Soy Sauce (Premium)** - SOY + GLUTEN (multiple standard allergens)
8. **Fresh Basil** - No allergens
9. **Sesame Seeds** - SESAME
10. **Celery Sticks** - CELERY

### Preparation (1 item)
- **Fresh Pasta Dough** - Uses Flour + Eggs
  - **Propagated Allergens**: EGGS, GLUTEN (sorted alphabetically)

### Recipe (1 item)
- **Truffle Pasta with Nuts**
  - **Uses**: Fresh Pasta Dough (prep) + White Truffle Oil + Mixed Nuts + Fresh Basil
  - **Aggregated Allergens**:
    - Standard: EGGS, GLUTEN, TREE_NUTS
    - Custom: Artificial Truffle Flavoring, White Truffle Extract

---

## ✅ Acceptance Criteria

### Must Pass
- [ ] All standard allergens stored as uppercase codes in database
- [ ] Allergen badges display with correct localized labels (EN/IT)
- [ ] Search and filter work correctly on Ingredients and Recipes pages
- [ ] Allergen propagation: Ingredients → Preparations → Recipes
- [ ] Custom allergens preserved as user input (not normalized)
- [ ] Language switching updates all allergen labels immediately
- [ ] RBAC: Staff cannot edit, Admin/Manager can edit
- [ ] No duplicate allergens in aggregated lists
- [ ] Orange badges for custom allergens, red for standard

### Nice to Have
- [ ] Allergen filter dropdown shows allergen count (e.g., "GLUTEN (5)")
- [ ] Filter persists when navigating between pages
- [ ] Allergen badges sorted alphabetically

---

## 🔧 Technical Details

### Backend Endpoints Tested
- `POST /api/ingredients` - Create with allergens
- `GET /api/ingredients` - List all (filter by restaurant)
- `GET /api/ingredients/{id}` - Get single ingredient
- `PUT /api/ingredients/{id}` - Update allergens
- `POST /api/preparations` - Auto-compute allergens
- `POST /api/recipes` - Aggregate allergens from items

### Data Migration
- Legacy "allergen" field automatically migrated to "allergens" array
- Unmatched allergen names moved to "otherAllergens"
- All allergen codes uppercased on save

### Code Storage Format
```json
{
  "allergens": ["GLUTEN", "DAIRY"],
  "otherAllergens": ["truffle extract", "special seasoning"]
}
```

---

## 🐛 Known Issues

None at this time. All critical allergen functionality is working as expected.

---

## 📞 Support

For issues during UAT:
1. Check browser console for errors (F12)
2. Verify you're using correct credentials
3. Try clearing browser cache and reloading
4. Test in incognito mode to rule out browser extensions

---

## 🚀 Next Steps After UAT Approval

1. **Phase 6 Completion**: Receiving UI enhancements + tests
2. **Phase 7**: RBAC Matrix (customizable permissions)
3. **Phase 8**: Document Ingestion / OCR for price lists

---

## 📝 Test Results Template

Please fill this out during UAT:

| Test Scenario | Status | Notes |
|---------------|--------|-------|
| Create ingredient with standard allergens | ⬜ Pass / ❌ Fail | |
| Create ingredient with custom allergens | ⬜ Pass / ❌ Fail | |
| Search ingredients | ⬜ Pass / ❌ Fail | |
| Filter by allergen | ⬜ Pass / ❌ Fail | |
| View preparation allergens | ⬜ Pass / ❌ Fail | |
| View recipe allergens | ⬜ Pass / ❌ Fail | |
| Search recipes | ⬜ Pass / ❌ Fail | |
| Filter recipes by allergen | ⬜ Pass / ❌ Fail | |
| Switch to Italian | ⬜ Pass / ❌ Fail | |
| Allergen labels in Italian | ⬜ Pass / ❌ Fail | |
| Switch back to English | ⬜ Pass / ❌ Fail | |
| Staff read-only access | ⬜ Pass / ❌ Fail | |
| Manager edit access | ⬜ Pass / ❌ Fail | |

**Overall UAT Result**: ⬜ Approved / ❌ Rejected

**Tester Name**: ____________________
**Date**: ____________________
**Additional Comments**:
