# RistoBrain - Restaurant Cost Control Platform

Multi-tenant restaurant ERP system with comprehensive cost management, inventory tracking, and financial reporting.

## Tech Stack

- **Frontend**: React 19 + Tailwind CSS + shadcn/ui
- **Backend**: FastAPI + Python 3.11
- **Database**: MongoDB
- **Auth**: JWT with bcrypt
- **Email**: SMTP (with console fallback)

## Features

### Phase 1 (Current - Foundations)
- ✅ Multi-currency support (EUR/USD, extensible)
- ✅ Role-Based Access Control (RBAC) with customizable permissions
- ✅ Password reset flow with email
- ✅ Internationalization (English/Italian)
- ✅ Multi-tenant isolation by restaurantId
- ✅ Dashboard with KPIs
- ✅ Ingredients management
- ✅ Recipe builder with cost calculator
- ✅ Inventory tracking with expiry alerts
- ✅ Sales recording
- ✅ Wastage logging
- ✅ P&L snapshots

## Quick Start

### Prerequisites
```bash
Python 3.11+
Node.js 18+
MongoDB 5.0+
```

### Environment Setup
```bash
cd /app/backend
cp .env.example .env
# Edit .env with your configuration
```

### Seed Test Data
```bash
cd /app/backend
python3 seed_test_data.py
```

**Test Users**:
- `admin@test.com` / `admin123` (Administrator)
- `manager@test.com` / `manager123` (Manager)
- `staff@test.com` / `staff123` (Waiter)

### Access Application
- **URL**: https://ristobrain-menu.preview.emergentagent.com
- **Health**: https://ristobrain-menu.preview.emergentagent.com/api/health
- **API Docs**: https://ristobrain-menu.preview.emergentagent.com/docs

## Database Migration

### Convert to Minor Units (MONETARY_V1)

**Preview (Dry-run)**:
```bash
python3 migrate_to_minor_units.py --dry-run
```

**Execute**:
```bash
# Set MIGRATION_MONETARY_V1=true in .env
python3 migrate_to_minor_units.py
```

## Multi-Currency

### Storage
All amounts in **minor units** (cents):
- €8.50 → 850
- $8.50 → 850

### API Response
```json
{
  "price": {
    "value": 850,
    "currency": "EUR",
    "decimal": 8.50,
    "formatted": "€ 8,50"
  }
}
```

## RBAC & Permissions

### Default Roles
- **Administrator**: Full access
- **Manager**: Read/write, no deletes or settings
- **Waiter**: Sales/inventory only

### Permission Keys
```
ingredients.*
recipes.*
inventory.*
sales.*
wastage.*
pl.*
dashboard.read
settings.*
```

## Password Reset

1. User requests reset at `/auth/forgot`
2. Email sent with one-time token (60 min TTL)
3. User resets password at `/reset?token=...`
4. Token consumed and sessions invalidated

**Security**:
- Rate limited (3/5min)
- SHA-256 hashed tokens
- Single-use only
- Localized emails (EN/IT)

## Key Endpoints

```bash
GET  /api/health              # Health check
POST /api/auth/register       # Register
POST /api/auth/login          # Login
POST /api/auth/forgot         # Request reset
POST /api/auth/reset          # Reset password
GET  /api/dashboard/kpis      # Dashboard data
```

## Configuration

Edit `/app/backend/.env`:
```env
DEFAULT_CURRENCY=EUR
DEFAULT_LOCALE=it-IT
SUPPORTED_CURRENCIES=EUR,USD
SUPPORTED_LOCALES=en-US,it-IT
SMTP_HOST=                    # Optional
APP_URL=https://your-domain.com
```

## Roadmap

### Phase 2 (Next)
- Settings UI
- Password reset UI
- Language switcher
- RBAC management UI

### Phase 3
- Preparations module
- Receiving & OCR
- Forecasting
- Suppliers

## Support

- Logs: `/var/log/supervisor/backend.err.log`
- API Docs: `/docs` (FastAPI auto-generated)
- Database: `mongosh`

## License
Proprietary
