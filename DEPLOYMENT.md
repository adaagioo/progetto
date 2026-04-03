# RistoBrain Deployment Guide

## Overview

RistoBrain is a multi-tenant restaurant ERP application for cost control, inventory tracking, and financial reporting.

## Tech Stack

- **Frontend**: React 19 + Tailwind CSS + shadcn/ui
- **Backend**: FastAPI + Python 3.11
- **Database**: MongoDB
- **Auth**: JWT with bcrypt
- **Email**: SMTP (mock placeholder for development)

## Environment Setup

### Backend Environment Variables

Create `/app/backend/.env` from the template:

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `ENV` | Yes | Environment name | `staging`, `production` |
| `DEBUG` | Yes | Debug mode | `false` for production |
| `LOG_LEVEL` | No | Logging level | `INFO`, `WARNING` |
| `ALLOW_ORIGINS` | Yes | CORS origins (JSON array) | `["https://your-domain.com"]` |
| `APP_URL` | Yes | Frontend URL for email links | `https://your-domain.com` |
| `MONGO_URI` | Yes | MongoDB connection string | `mongodb://localhost:27017/ristobrain` |
| `MONGO_DB_NAME` | Yes | Database name | `ristobrain` |
| `JWT_SECRET` | **Yes** | Secret for JWT signing (min 32 chars) | Generate with `python3 -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | JWT access token TTL | `1440` (24 hours) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | Refresh token TTL | `30` |
| `SMTP_HOST` | No | SMTP server host | `smtp.gmail.com` |
| `SMTP_PORT` | No | SMTP server port | `587` |
| `SMTP_USER` | No | SMTP username | `your-email@gmail.com` |
| `SMTP_PASS` | No | SMTP password | `app-specific-password` |
| `MAIL_FROM` | No | Email sender | `RistoBrain <no-reply@domain.com>` |
| `STORAGE_DRIVER` | No | File storage driver | `local`, `s3` |
| `STORAGE_LOCAL_PATH` | No | Local storage path | `/data/storage` |
| `DEFAULT_CURRENCY` | No | Default currency | `EUR` |
| `DEFAULT_LOCALE` | No | Default locale | `it-IT` |

### Frontend Environment Variables

Create `/app/frontend/.env`:

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `REACT_APP_BACKEND_URL` | Yes | Backend API base URL | `https://your-domain.com` |

### Environment-Specific Configuration

#### Staging
```bash
# /app/frontend/.env
REACT_APP_BACKEND_URL=https://your-staging-domain.emergentagent.com

# /app/backend/.env  
ENV=staging
APP_URL=https://your-staging-domain.emergentagent.com
ALLOW_ORIGINS=["*"]
```

#### Production
```bash
# /app/frontend/.env
REACT_APP_BACKEND_URL=https://your-production-domain.com

# /app/backend/.env
ENV=production
DEBUG=false
APP_URL=https://your-production-domain.com
ALLOW_ORIGINS=["https://your-production-domain.com"]
# Generate new JWT_SECRET for production!
JWT_SECRET=<new-unique-secret>
```

## Deployment Preparation

### 1. Generate JWT Secret

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

### 2. Create Environment Files

**Staging:**
```bash
# Backend
cp /app/backend/.env.production.template /app/backend/.env
# Edit with staging values

# Frontend
cp /app/frontend/.env.production.template /app/frontend/.env
# Edit with staging URL
```

**Production:**
Use the same templates with production-specific values.

### 3. Seed Super Admin

```bash
cd /app/backend
python3 seed_super_admin.py
```

Default credentials:
- Email: `admin@ristobrain.app`
- Password: `ChangeMe123!`

**⚠️ IMPORTANT: Change this password immediately after first login!**

### 4. (Optional) Seed Test Data

```bash
cd /app/backend
python3 seed_test_data.py
```

Creates:
- `admin@test.com` / `admin123`
- `manager@test.com` / `manager123`
- `staff@test.com` / `staff123`

## Deployment Checklist

### Pre-deployment

- [ ] JWT_SECRET is unique and secure (min 32 chars)
- [ ] MONGO_URI points to production MongoDB
- [ ] ALLOW_ORIGINS contains only your domain
- [ ] APP_URL matches your production frontend URL
- [ ] REACT_APP_BACKEND_URL matches your production backend
- [ ] SMTP configured (or disabled for initial testing)
- [ ] Super admin seeded

### Post-deployment

- [ ] Health check responds: `GET /api/health/live`
- [ ] Login works with super admin
- [ ] Change super admin password
- [ ] Test user creation flow
- [ ] Verify multi-tenant isolation

## API Endpoints

### Health
- `GET /api/health/live` - Liveness probe
- `GET /api/health/ready` - Readiness probe (checks DB)

### Auth
- `POST /api/auth/login` - User login
- `POST /api/auth/register` - User registration
- `POST /api/auth/forgot` - Password reset request
- `POST /api/auth/reset` - Password reset
- `GET /api/auth/me` - Current user info

### Documentation
- `GET /docs` - Swagger UI
- `GET /redoc` - ReDoc
- `GET /openapi.json` - OpenAPI schema

## Security Notes

1. **JWT_SECRET**: Never commit to version control. Use environment variables only.
2. **CORS**: Restrict `ALLOW_ORIGINS` to your specific domain(s).
3. **Rate Limiting**: Login and password reset have built-in rate limiting.
4. **Password Reset**: Tokens expire after 30 minutes and are single-use.

## Troubleshooting

### Backend won't start

1. Check logs: `tail -f /var/log/supervisor/backend.err.log`
2. Verify JWT_SECRET is at least 32 characters
3. Verify MONGO_URI is valid and MongoDB is accessible

### Frontend can't connect to backend

1. Verify REACT_APP_BACKEND_URL is correct
2. Check CORS settings in backend (ALLOW_ORIGINS)
3. Verify backend is running: `curl http://localhost:8001/api/health/live`

### Login fails

1. Check if user exists in database
2. Verify password hash is valid
3. Check JWT_SECRET hasn't changed

## Support

- Logs: `/var/log/supervisor/backend.err.log`
- API Docs: `/docs`
- Database: `mongosh`
