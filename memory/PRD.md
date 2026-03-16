# RistoBrain PRD - Deployment Preparation

## Original Problem Statement
Import and prepare existing GitHub repository (RistoBrain multi-tenant restaurant ERP) for cloud deployment on Emergent while keeping the repository structure and current implementation intact.

## Architecture
- **Frontend**: React 19 + Tailwind CSS + shadcn/ui
- **Backend**: FastAPI + Python 3.11
- **Database**: MongoDB (preserved as required)
- **Auth**: JWT with bcrypt/pbkdf2_sha256
- **Email**: SMTP (mock placeholder for testing)

## User Personas
1. **Super Admin** (owner role) - Full system access
2. **Admin** - Full access except RBAC management
3. **Manager** - Operational access, limited admin functions
4. **Staff/Waiter** - Read-only with sales/inventory access

## Core Requirements
- Multi-tenant isolation by restaurantId ✅
- JWT-based authentication ✅
- RBAC system with customizable roles ✅
- Bilingual support (English/Italian) ✅
- Mobile-responsive UI ✅
- MongoDB as database ✅

## What's Been Implemented (March 16, 2026)

### Blocking Issues Fixed
1. **Created `/app/backend/app/repositories/restaurant_repo.py`**
   - Missing repository causing import errors
   - Added `find_by_id`, `upsert`, `create` functions

2. **Created `/app/backend/server.py`**
   - Bridge file for Emergent supervisor compatibility
   - Imports FastAPI app from main.py

3. **Created `/app/backend/.env`**
   - Staging environment configuration
   - JWT_SECRET, MONGO_URI, CORS settings

4. **Created `/app/frontend/.env`**
   - REACT_APP_BACKEND_URL for API calls

5. **Fixed `/app/backend/seed_test_data.py`**
   - Corrected import path for rbac_utils
   - Fixed MONGO_URL vs MONGO_URI env variable names

6. **Created `/app/backend/seed_super_admin.py`**
   - Seeds default super admin user
   - Credentials: admin@ristobrain.app / ChangeMe123!

7. **Fixed `/app/backend/app/api/V1/user.py`**
   - Fixed import error (inventory_repo → users_repo)
   - Added extended user schemas for frontend compatibility
   - Added temp password generation

8. **Updated `/app/backend/app/repositories/users_repo.py`**
   - Added `create_user_extended` function
   - Added displayName and isDisabled fields support

### Environment Templates Created
- `/app/backend/.env.production.template`
- `/app/frontend/.env.production.template`

### Documentation Created
- `/app/DEPLOYMENT.md` - Complete deployment guide

## Test Results (March 16, 2026)
- Backend: 100% passed
- Frontend: 100% passed
- Integration: 100% passed

## Prioritized Backlog

### P0 (Required for Production)
- [ ] Configure real SMTP credentials
- [ ] Set production-specific JWT_SECRET
- [ ] Configure production CORS origins
- [ ] Change super admin password after deployment

### P1 (Recommended)
- [ ] Email invite flow for user creation
- [ ] Per-restaurant tenant data isolation verification
- [ ] Production MongoDB with authentication

### P2 (Future)
- [ ] S3/cloud storage configuration
- [ ] Advanced OCR integration
- [ ] Performance monitoring

## Next Tasks
1. Obtain SMTP credentials from user
2. Configure production environment with actual domain
3. Deploy to staging for user testing
4. Deploy to production after staging approval

## Files Changed Summary

| File | Action | Reason |
|------|--------|--------|
| `/app/backend/app/repositories/restaurant_repo.py` | Created | Missing file causing import error |
| `/app/backend/server.py` | Created | Bridge for Emergent supervisor |
| `/app/backend/.env` | Created | Required configuration |
| `/app/frontend/.env` | Created | Backend URL configuration |
| `/app/backend/seed_test_data.py` | Modified | Fixed import paths |
| `/app/backend/seed_super_admin.py` | Created | Super admin seeder |
| `/app/backend/app/api/V1/user.py` | Modified | Fixed import, added extended schemas |
| `/app/backend/app/repositories/users_repo.py` | Modified | Added extended user creation |
| `/app/backend/.env.production.template` | Created | Production template |
| `/app/frontend/.env.production.template` | Created | Production template |
| `/app/DEPLOYMENT.md` | Created | Deployment documentation |
