from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt
import hashlib
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from rbac_utils import get_user_permissions, seed_default_roles, has_permission
from email_templates import get_reset_email_template, get_password_changed_email_template
from i18n_messages import get_message
from storage_service import init_storage_service, get_storage_service
from audit_utils import log_audit

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10080  # 7 days

# App Configuration
DEFAULT_CURRENCY = os.environ.get('DEFAULT_CURRENCY', 'EUR')
DEFAULT_LOCALE = os.environ.get('DEFAULT_LOCALE', 'it-IT')
SUPPORTED_CURRENCIES = os.environ.get('SUPPORTED_CURRENCIES', 'EUR,USD').split(',')
SUPPORTED_LOCALES = os.environ.get('SUPPORTED_LOCALES', 'en-US,it-IT').split(',')

# Email Configuration
SMTP_HOST = os.environ.get('SMTP_HOST', '')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASS = os.environ.get('SMTP_PASS', '')
MAIL_FROM = os.environ.get('MAIL_FROM', 'RistoBrain <no-reply@ristobrain.app>')
APP_URL = os.environ.get('APP_URL', 'http://localhost:3000')

# Storage Configuration
STORAGE_DRIVER = os.environ.get('STORAGE_DRIVER', 'local')
UPLOAD_BASE_PATH = os.environ.get('UPLOAD_BASE_PATH', '/app/uploads')
UPLOAD_MAX_MB = int(os.environ.get('UPLOAD_MAX_MB', 10))
UPLOAD_ALLOWED_MIME = os.environ.get(
    'UPLOAD_ALLOWED_MIME',
    'application/pdf,image/jpeg,image/png'
)

# Initialize storage service
init_storage_service(
    driver_type=STORAGE_DRIVER,
    base_path=UPLOAD_BASE_PATH,
    max_size_mb=UPLOAD_MAX_MB,
    allowed_mimes=UPLOAD_ALLOWED_MIME
)

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

# ============ MODELS ============

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    displayName: str
    restaurantName: str
    locale: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    newPassword: str

class UpdateLocaleRequest(BaseModel):
    locale: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: Dict[str, Any]

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    displayName: str
    restaurantId: str
    role: str
    roleKey: Optional[str] = "admin"
    locale: Optional[str] = None
    createdAt: str

class Restaurant(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    plan: str = "Starter"
    subscriptionStatus: str = "active"
    ownerUserId: str
    currency: Optional[Dict[str, Any]] = None
    defaultLocale: Optional[str] = None
    createdAt: str

class ShelfLife(BaseModel):
    """Shelf life specification"""
    value: int
    unit: str  # 'days', 'weeks', 'months'

class IngredientCreate(BaseModel):
    name: str
    unit: str
    packSize: float
    packCost: float
    supplier: Optional[str] = None
    allergen: Optional[str] = None  # Deprecated, use allergens array
    allergens: Optional[List[str]] = []  # EU-14 + Other
    minStockQty: float = 0
    category: Optional[str] = "food"  # food, beverage, nofood
    wastePct: Optional[float] = 0  # 0-100%
    shelfLife: Optional[ShelfLife] = None

class Ingredient(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    restaurantId: str
    name: str
    unit: str
    packSize: float
    packCost: float
    unitCost: float
    effectiveUnitCost: float  # unitCost * (1 + wastePct/100)
    supplier: Optional[str] = None
    allergen: Optional[str] = None  # Deprecated
    allergens: List[str] = []
    minStockQty: float
    category: str = "food"
    wastePct: float = 0
    shelfLife: Optional[ShelfLife] = None
    createdAt: str

class PreparationItem(BaseModel):
    """Item in a preparation (raw ingredient only in v1)"""
    ingredientId: str
    qty: float
    unit: str

class Yield(BaseModel):
    """Preparation yield"""
    value: float
    unit: str

class PreparationCreate(BaseModel):
    """Create preparation request"""
    name: str
    items: List[PreparationItem]
    yield_: Optional[Yield] = None
    shelfLife: Optional[ShelfLife] = None
    notes: Optional[str] = None

class PreparationUpdate(BaseModel):
    """Update preparation request"""
    name: Optional[str] = None
    items: Optional[List[PreparationItem]] = None
    yield_: Optional[Yield] = None
    shelfLife: Optional[ShelfLife] = None
    notes: Optional[str] = None

class Preparation(BaseModel):
    """Preparation model"""
    model_config = ConfigDict(extra="ignore")
    id: str
    restaurantId: str
    name: str
    items: List[PreparationItem]
    yield_: Optional[Yield] = None
    shelfLife: Optional[ShelfLife] = None
    notes: Optional[str] = None
    cost: float  # Computed from ingredients with waste
    allergens: List[str]  # Computed from ingredients
    createdAt: str
    updatedAt: Optional[str] = None

class InventoryCreate(BaseModel):
    ingredientId: str
    qty: float
    unit: str
    countType: str
    batchExpiry: Optional[str] = None
    location: Optional[str] = None

class Inventory(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    restaurantId: str
    ingredientId: str
    qty: float
    unit: str
    countType: str
    batchExpiry: Optional[str] = None
    location: Optional[str] = None
    createdAt: str

class RecipeItem(BaseModel):
    """Item in a recipe - can be ingredient or preparation"""
    type: str  # 'ingredient' or 'preparation'
    itemId: str  # ingredientId or preparationId
    qtyPerPortion: float
    unit: str

class RecipeCreate(BaseModel):
    name: str
    category: str
    portions: int
    targetFoodCostPct: float
    price: float
    items: List[RecipeItem]
    shelfLife: Optional[ShelfLife] = None

class RecipeUpdate(BaseModel):
    """Update recipe request"""
    name: Optional[str] = None
    category: Optional[str] = None
    portions: Optional[int] = None
    targetFoodCostPct: Optional[float] = None
    price: Optional[float] = None
    items: Optional[List[RecipeItem]] = None
    shelfLife: Optional[ShelfLife] = None

class Recipe(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    restaurantId: str
    name: str
    category: str
    portions: int
    targetFoodCostPct: float
    price: float
    items: List[RecipeItem]
    allergens: List[str] = []  # Computed from all items
    shelfLife: Optional[ShelfLife] = None
    createdAt: str
    updatedAt: Optional[str] = None

class SaleLine(BaseModel):
    recipeId: str
    qty: int

class SalesCreate(BaseModel):
    date: str
    lines: List[SaleLine]

class Sales(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    restaurantId: str
    date: str
    lines: List[SaleLine]
    createdAt: str

class WastageCreate(BaseModel):
    date: str
    type: str
    ingredientId: Optional[str] = None
    recipeId: Optional[str] = None
    qty: float
    unit: str
    reason: Optional[str] = None

class Wastage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    restaurantId: str
    date: str
    type: str
    ingredientId: Optional[str] = None
    recipeId: Optional[str] = None
    qty: float
    unit: str
    reason: Optional[str] = None
    createdAt: str

class PLCreate(BaseModel):
    month: str
    revenue: float
    cogs: float
    grossMargin: float
    notes: Optional[str] = None

class PL(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    restaurantId: str
    month: str
    revenue: float
    cogs: float
    grossMargin: float
    notes: Optional[str] = None
    createdAt: str

class FileMetadata(BaseModel):
    """File metadata model"""
    id: str
    restaurantId: str
    filename: str
    path: str
    size: int
    mimeType: str
    hash: str
    uploadedBy: str
    uploadedAt: str

class SupplierContact(BaseModel):
    """Supplier contact information"""
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

class SupplierCreate(BaseModel):
    """Create supplier request"""
    name: str
    contacts: Optional[SupplierContact] = None
    notes: Optional[str] = None

class SupplierUpdate(BaseModel):
    """Update supplier request"""
    name: Optional[str] = None
    contacts: Optional[SupplierContact] = None
    notes: Optional[str] = None

class Supplier(BaseModel):
    """Supplier model"""
    model_config = ConfigDict(extra="ignore")
    id: str
    restaurantId: str
    name: str
    contacts: Optional[SupplierContact] = None
    notes: Optional[str] = None
    files: List[FileMetadata] = []
    createdAt: str
    updatedAt: Optional[str] = None

class ReceivingLine(BaseModel):
    """Line item in a receiving record"""
    ingredientId: Optional[str] = None
    description: str
    qty: float
    unit: str
    unitPrice: float  # in minor units (cents)
    packFormat: Optional[str] = None
    expiryDate: Optional[str] = None

class ReceivingCreate(BaseModel):
    """Create receiving request"""
    supplierId: str
    category: str  # 'food', 'beverage', 'nofood'
    lines: List[ReceivingLine]
    arrivedAt: str
    notes: Optional[str] = None

class ReceivingUpdate(BaseModel):
    """Update receiving request"""
    supplierId: Optional[str] = None
    category: Optional[str] = None
    lines: Optional[List[ReceivingLine]] = None
    arrivedAt: Optional[str] = None
    notes: Optional[str] = None

class Receiving(BaseModel):
    """Receiving model"""
    model_config = ConfigDict(extra="ignore")
    id: str
    restaurantId: str
    supplierId: str
    category: str
    lines: List[ReceivingLine]
    total: float  # in minor units, calculated from lines
    files: List[FileMetadata] = []
    arrivedAt: str
    notes: Optional[str] = None
    createdAt: str
    updatedAt: Optional[str] = None

# ============ AUTH HELPERS ============

async def send_email(to_email: str, subject: str, body: str):
    """Send email via SMTP"""
    if not SMTP_HOST or not SMTP_USER:
        logger.warning(f"Email not configured. Would send:\nTo: {to_email}\nSubject: {subject}\n{body}\n{'='*60}\n")
        return
    
    try:
        message = MIMEText(body, "html")
        message["From"] = MAIL_FROM
        message["To"] = to_email
        message["Subject"] = subject
        
        async with aiosmtplib.SMTP(
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            use_tls=True,
            username=SMTP_USER,
            password=SMTP_PASS,
        ) as smtp:
            await smtp.send_message(message)
        logger.info(f"Email sent successfully to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        raise

# ============ PREPARATION HELPERS ============

async def compute_preparation_cost_and_allergens(items: List[dict], db) -> tuple[float, List[str]]:
    """
    Compute preparation cost and allergens from ingredient items.
    Cost includes waste percentage: effectiveUnitCost * qty
    """
    total_cost = 0
    all_allergens = set()
    
    for item in items:
        ingredient = await db.ingredients.find_one({"id": item["ingredientId"]}, {"_id": 0})
        if not ingredient:
            continue
        
        # Use effectiveUnitCost which includes waste
        effective_cost = ingredient.get("effectiveUnitCost", ingredient.get("unitCost", 0))
        item_cost = effective_cost * item["qty"]
        total_cost += item_cost
        
        # Collect allergens
        allergens = ingredient.get("allergens", [])
        if allergens:
            all_allergens.update(allergens)
        
        # Legacy support for single allergen field
        if ingredient.get("allergen"):
            all_allergens.add(ingredient["allergen"])
    
    return total_cost, sorted(list(all_allergens))

async def compute_recipe_allergens(items: List[dict], db) -> List[str]:
    """
    Compute recipe allergens from all items (ingredients + preparations).
    Returns union of all allergens.
    """
    all_allergens = set()
    
    for item in items:
        if item["type"] == "ingredient":
            ingredient = await db.ingredients.find_one({"id": item["itemId"]}, {"_id": 0})
            if ingredient:
                allergens = ingredient.get("allergens", [])
                if allergens:
                    all_allergens.update(allergens)
                # Legacy support
                if ingredient.get("allergen"):
                    all_allergens.add(ingredient["allergen"])
        
        elif item["type"] == "preparation":
            preparation = await db.preparations.find_one({"id": item["itemId"]}, {"_id": 0})
            if preparation:
                allergens = preparation.get("allergens", [])
                if allergens:
                    all_allergens.update(allergens)
    
    return sorted(list(all_allergens))

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user

async def check_subscription(user: dict):
    restaurant = await db.restaurants.find_one({"id": user["restaurantId"]}, {"_id": 0})
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    
    if restaurant.get("subscriptionStatus") == "suspended":
        raise HTTPException(status_code=403, detail="Subscription suspended")
    
    return restaurant

# ============ AUTH ROUTES ============

@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check DB connection
        await db.command("ping")
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": "connected",
            "currency": DEFAULT_CURRENCY,
            "locale": DEFAULT_LOCALE
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserRegister):
    # Check if user exists
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password
    hashed_password = bcrypt.hashpw(user_data.password.encode('utf-8'), bcrypt.gensalt())
    
    # Create restaurant with currency and locale
    restaurant_id = str(uuid.uuid4())
    restaurant = {
        "id": restaurant_id,
        "name": user_data.restaurantName,
        "plan": "Starter",
        "subscriptionStatus": "active",
        "ownerUserId": str(uuid.uuid4()),
        "currency": {
            "code": DEFAULT_CURRENCY,
            "symbol": "€" if DEFAULT_CURRENCY == "EUR" else "$",
            "decimals": 2
        },
        "defaultLocale": DEFAULT_LOCALE,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    await db.restaurants.insert_one(restaurant)
    
    # Seed default roles for restaurant
    await seed_default_roles(db, restaurant_id)
    
    # Create user with locale
    user_id = str(uuid.uuid4())
    user_locale = user_data.locale or DEFAULT_LOCALE
    user = {
        "id": user_id,
        "email": user_data.email,
        "password": hashed_password.decode('utf-8'),
        "displayName": user_data.displayName,
        "restaurantId": restaurant_id,
        "role": "admin",
        "roleKey": "admin",
        "locale": user_locale,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user)
    
    # Create token
    token = create_access_token({"sub": user_id})
    
    user_response = {
        "id": user_id,
        "email": user["email"],
        "displayName": user["displayName"],
        "restaurantId": restaurant_id,
        "role": user["role"],
        "roleKey": user["roleKey"],
        "locale": user_locale
    }
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user_response
    }

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Verify password
    if not bcrypt.checkpw(credentials.password.encode('utf-8'), user["password"].encode('utf-8')):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create token
    token = create_access_token({"sub": user["id"]})
    
    user_response = {
        "id": user["id"],
        "email": user["email"],
        "displayName": user["displayName"],
        "restaurantId": user["restaurantId"],
        "role": user["role"],
        "roleKey": user.get("roleKey", "admin"),
        "locale": user.get("locale", DEFAULT_LOCALE)
    }
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user_response
    }

@api_router.get("/auth/me", response_model=User)
async def get_me(current_user: dict = Depends(get_current_user)):
    return User(**current_user)

# ============ PASSWORD RESET ROUTES ============

# Rate limiting tracking (in-memory for MVP; use Redis in production)
reset_attempts = {}

@api_router.post("/auth/forgot")
async def forgot_password(request: ForgotPasswordRequest):
    """Request password reset - sends email with reset token"""
    email = request.email
    
    # Rate limiting check
    now = datetime.now(timezone.utc)
    if email in reset_attempts:
        last_attempt, count = reset_attempts[email]
        if (now - last_attempt).seconds < 300 and count >= 3:  # 3 attempts per 5 min
            raise HTTPException(status_code=429, detail="Too many requests. Please try again later")
    
    # Find user
    user = await db.users.find_one({"email": email})
    if not user:
        # Don't reveal if email exists
        return {"message": "If the email exists, a reset link has been sent"}
    
    # Generate reset token
    token = str(uuid.uuid4())
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires_at = now + timedelta(minutes=60)
    
    # Store reset token
    await db.passwordResetTokens.insert_one({
        "userId": user["id"],
        "tokenHash": token_hash,
        "expiresAt": expires_at.isoformat(),
        "consumed": False,
        "createdAt": now.isoformat(),
        "ipMeta": {}  # Add request IP in production
    })
    
    # Send email
    reset_url = f"{APP_URL}/reset?token={token}"
    user_locale = user.get("locale", DEFAULT_LOCALE)
    email_template = get_reset_email_template(user_locale, reset_url, user["displayName"])
    
    await send_email(
        to_email=email,
        subject=email_template["subject"],
        body=email_template["body"]
    )
    
    # Update rate limit tracking
    if email in reset_attempts:
        reset_attempts[email] = (now, reset_attempts[email][1] + 1)
    else:
        reset_attempts[email] = (now, 1)
    
    return {"message": "If the email exists, a reset link has been sent"}

@api_router.post("/auth/reset")
async def reset_password(request: ResetPasswordRequest):
    """Reset password using token"""
    token = request.token
    new_password = request.newPassword
    
    # Hash token to find in DB
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    # Find token
    reset_token = await db.passwordResetTokens.find_one({"tokenHash": token_hash})
    
    if not reset_token:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    # Check if consumed
    if reset_token["consumed"]:
        raise HTTPException(status_code=400, detail="Reset token already used")
    
    # Check if expired
    expires_at = datetime.fromisoformat(reset_token["expiresAt"].replace('Z', '+00:00'))
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=400, detail="Reset token expired")
    
    # Find user
    user = await db.users.find_one({"id": reset_token["userId"]})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Hash new password
    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
    
    # Update password
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"password": hashed_password.decode('utf-8')}}
    )
    
    # Mark token as consumed
    await db.passwordResetTokens.update_one(
        {"_id": reset_token["_id"]},
        {"$set": {"consumed": True, "consumedAt": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Send confirmation email
    user_locale = user.get("locale", DEFAULT_LOCALE)
    email_template = get_password_changed_email_template(user_locale, user["displayName"])
    
    await send_email(
        to_email=user["email"],
        subject=email_template["subject"],
        body=email_template["body"]
    )
    
    return {"message": "Password reset successful"}

# ============ USER PROFILE ROUTES ============

@api_router.put("/auth/locale")
async def update_locale(request: UpdateLocaleRequest, current_user: dict = Depends(get_current_user)):
    """Update user locale"""
    locale = request.locale
    
    if locale not in SUPPORTED_LOCALES:
        raise HTTPException(status_code=400, detail=f"Unsupported locale. Choose from: {', '.join(SUPPORTED_LOCALES)}")
    
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$set": {"locale": locale}}
    )
    
    return {"message": "Locale updated successfully", "locale": locale}

# ============ INGREDIENTS ROUTES ============

@api_router.post("/ingredients", response_model=Ingredient)
async def create_ingredient(ingredient_data: IngredientCreate, current_user: dict = Depends(get_current_user)):
    await check_subscription(current_user)
    
    ingredient_id = str(uuid.uuid4())
    unit_cost = ingredient_data.packCost / ingredient_data.packSize
    waste_pct = ingredient_data.wastePct or 0
    effective_unit_cost = unit_cost * (1 + waste_pct / 100)
    
    ingredient = {
        "id": ingredient_id,
        "restaurantId": current_user["restaurantId"],
        "name": ingredient_data.name,
        "unit": ingredient_data.unit,
        "packSize": ingredient_data.packSize,
        "packCost": ingredient_data.packCost,
        "unitCost": unit_cost,
        "effectiveUnitCost": effective_unit_cost,
        "supplier": ingredient_data.supplier,
        "allergen": ingredient_data.allergen,
        "allergens": ingredient_data.allergens or [],
        "minStockQty": ingredient_data.minStockQty,
        "category": ingredient_data.category or "food",
        "wastePct": waste_pct,
        "shelfLife": ingredient_data.shelfLife.dict() if ingredient_data.shelfLife else None,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.ingredients.insert_one(ingredient)
    return Ingredient(**ingredient)

@api_router.get("/ingredients", response_model=List[Ingredient])
async def get_ingredients(current_user: dict = Depends(get_current_user)):
    await check_subscription(current_user)
    ingredients = await db.ingredients.find({"restaurantId": current_user["restaurantId"]}, {"_id": 0}).to_list(1000)
    return [Ingredient(**ing) for ing in ingredients]

@api_router.put("/ingredients/{ingredient_id}", response_model=Ingredient)
async def update_ingredient(ingredient_id: str, ingredient_data: IngredientCreate, current_user: dict = Depends(get_current_user)):
    await check_subscription(current_user)
    
    existing = await db.ingredients.find_one({"id": ingredient_id, "restaurantId": current_user["restaurantId"]})
    if not existing:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    
    unit_cost = ingredient_data.packCost / ingredient_data.packSize
    waste_pct = ingredient_data.wastePct or 0
    effective_unit_cost = unit_cost * (1 + waste_pct / 100)
    
    update_data = {
        "name": ingredient_data.name,
        "unit": ingredient_data.unit,
        "packSize": ingredient_data.packSize,
        "packCost": ingredient_data.packCost,
        "unitCost": unit_cost,
        "effectiveUnitCost": effective_unit_cost,
        "supplier": ingredient_data.supplier,
        "allergen": ingredient_data.allergen,
        "allergens": ingredient_data.allergens or [],
        "minStockQty": ingredient_data.minStockQty,
        "wastePct": waste_pct,
        "shelfLife": ingredient_data.shelfLife.dict() if ingredient_data.shelfLife else None
    }
    
    await db.ingredients.update_one({"id": ingredient_id}, {"$set": update_data})
    updated = await db.ingredients.find_one({"id": ingredient_id}, {"_id": 0})
    return Ingredient(**updated)

@api_router.delete("/ingredients/{ingredient_id}")
async def delete_ingredient(ingredient_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.ingredients.delete_one({"id": ingredient_id, "restaurantId": current_user["restaurantId"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    
    return {"message": "Ingredient deleted"}

# ============ PREPARATIONS (SUB-RECIPES) ============

@api_router.post("/preparations", response_model=Preparation)
async def create_preparation(prep: PreparationCreate, current_user: dict = Depends(get_current_user)):
    """Create a new preparation (sub-recipe)"""
    await check_subscription(current_user)
    
    # Validate all ingredients exist
    for item in prep.items:
        ingredient = await db.ingredients.find_one(
            {"id": item.ingredientId, "restaurantId": current_user["restaurantId"]}
        )
        if not ingredient:
            raise HTTPException(status_code=404, detail=f"Ingredient {item.ingredientId} not found")
    
    # Compute cost and allergens
    items_dict = [item.dict() for item in prep.items]
    cost, allergens = await compute_preparation_cost_and_allergens(items_dict, db)
    
    preparation = {
        "id": str(uuid.uuid4()),
        "restaurantId": current_user["restaurantId"],
        "name": prep.name,
        "items": items_dict,
        "yield": prep.yield_.dict() if prep.yield_ else None,
        "shelfLife": prep.shelfLife.dict() if prep.shelfLife else None,
        "notes": prep.notes,
        "cost": cost,
        "allergens": allergens,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "updatedAt": None
    }
    
    await db.preparations.insert_one(preparation)
    
    # Log audit
    await log_audit(
        db,
        current_user["restaurantId"],
        current_user["id"],
        "create",
        "preparation",
        preparation["id"],
        {"name": prep.name, "cost": cost}
    )
    
    preparation.pop("_id", None)
    return Preparation(**preparation)

@api_router.get("/preparations", response_model=List[Preparation])
async def get_preparations(current_user: dict = Depends(get_current_user)):
    """Get all preparations for the restaurant"""
    await check_subscription(current_user)
    
    preparations = await db.preparations.find(
        {"restaurantId": current_user["restaurantId"]},
        {"_id": 0}
    ).to_list(1000)
    
    return [Preparation(**p) for p in preparations]

@api_router.get("/preparations/{prep_id}", response_model=Preparation)
async def get_preparation(prep_id: str, current_user: dict = Depends(get_current_user)):
    """Get a specific preparation"""
    await check_subscription(current_user)
    
    preparation = await db.preparations.find_one(
        {"id": prep_id, "restaurantId": current_user["restaurantId"]},
        {"_id": 0}
    )
    
    if not preparation:
        raise HTTPException(status_code=404, detail="Preparation not found")
    
    return Preparation(**preparation)

@api_router.put("/preparations/{prep_id}", response_model=Preparation)
async def update_preparation(
    prep_id: str,
    prep_update: PreparationUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a preparation"""
    await check_subscription(current_user)
    
    # Check if preparation exists
    existing = await db.preparations.find_one(
        {"id": prep_id, "restaurantId": current_user["restaurantId"]}
    )
    
    if not existing:
        raise HTTPException(status_code=404, detail="Preparation not found")
    
    # Build update data
    update_data = {}
    
    if prep_update.name is not None:
        update_data["name"] = prep_update.name
    
    if prep_update.items is not None:
        # Validate ingredients
        for item in prep_update.items:
            ingredient = await db.ingredients.find_one(
                {"id": item.ingredientId, "restaurantId": current_user["restaurantId"]}
            )
            if not ingredient:
                raise HTTPException(status_code=404, detail=f"Ingredient {item.ingredientId} not found")
        
        items_dict = [item.dict() for item in prep_update.items]
        update_data["items"] = items_dict
        
        # Recompute cost and allergens
        cost, allergens = await compute_preparation_cost_and_allergens(items_dict, db)
        update_data["cost"] = cost
        update_data["allergens"] = allergens
    
    if prep_update.yield_ is not None:
        update_data["yield"] = prep_update.yield_.dict()
    
    if prep_update.shelfLife is not None:
        update_data["shelfLife"] = prep_update.shelfLife.dict()
    
    if prep_update.notes is not None:
        update_data["notes"] = prep_update.notes
    
    update_data["updatedAt"] = datetime.now(timezone.utc).isoformat()
    
    # Update in database
    await db.preparations.update_one(
        {"id": prep_id},
        {"$set": update_data}
    )
    
    # Log audit
    await log_audit(
        db,
        current_user["restaurantId"],
        current_user["id"],
        "update",
        "preparation",
        prep_id,
        update_data
    )
    
    # Get updated preparation
    updated_prep = await db.preparations.find_one(
        {"id": prep_id},
        {"_id": 0}
    )
    
    return Preparation(**updated_prep)

@api_router.delete("/preparations/{prep_id}")
async def delete_preparation(prep_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a preparation"""
    await check_subscription(current_user)
    
    # Check if preparation exists
    preparation = await db.preparations.find_one(
        {"id": prep_id, "restaurantId": current_user["restaurantId"]},
        {"_id": 0}
    )
    
    if not preparation:
        raise HTTPException(status_code=404, detail="Preparation not found")
    
    # Delete preparation
    await db.preparations.delete_one({"id": prep_id})
    
    # Log audit
    await log_audit(
        db,
        current_user["restaurantId"],
        current_user["id"],
        "delete",
        "preparation",
        prep_id,
        {"name": preparation["name"]}
    )
    
    return {"message": "Preparation deleted"}

# ============ INVENTORY ROUTES ============

@api_router.post("/inventory", response_model=Inventory)
async def create_inventory(inventory_data: InventoryCreate, current_user: dict = Depends(get_current_user)):
    await check_subscription(current_user)
    
    inventory_id = str(uuid.uuid4())
    inventory = {
        "id": inventory_id,
        "restaurantId": current_user["restaurantId"],
        "ingredientId": inventory_data.ingredientId,
        "qty": inventory_data.qty,
        "unit": inventory_data.unit,
        "countType": inventory_data.countType,
        "batchExpiry": inventory_data.batchExpiry,
        "location": inventory_data.location,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.inventory.insert_one(inventory)
    return Inventory(**inventory)

@api_router.get("/inventory", response_model=List[Inventory])
async def get_inventory(current_user: dict = Depends(get_current_user)):
    await check_subscription(current_user)
    inventory = await db.inventory.find({"restaurantId": current_user["restaurantId"]}, {"_id": 0}).to_list(1000)
    return [Inventory(**inv) for inv in inventory]

@api_router.delete("/inventory/{inventory_id}")
async def delete_inventory(inventory_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.inventory.delete_one({"id": inventory_id, "restaurantId": current_user["restaurantId"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Inventory record not found")
    
    return {"message": "Inventory deleted"}

# ============ INVENTORY VALUATION & ADJUSTMENTS ============

@api_router.get("/inventory/valuation")
async def get_inventory_valuation(current_user: dict = Depends(get_current_user)):
    """Calculate weighted average cost for each ingredient"""
    await check_subscription(current_user)
    
    restaurant_id = current_user["restaurantId"]
    
    # Get all inventory records with unitCost
    inventory_records = await db.inventory.find(
        {"restaurantId": restaurant_id, "unitCost": {"$exists": True}},
        {"_id": 0}
    ).to_list(10000)
    
    # Get all ingredients to get category
    ingredients = await db.ingredients.find(
        {"restaurantId": restaurant_id},
        {"_id": 0}
    ).to_list(1000)
    
    ingredient_map = {ing["id"]: ing for ing in ingredients}
    
    # Calculate weighted average cost per ingredient
    valuation_data = {}
    
    for record in inventory_records:
        ingredient_id = record.get("ingredientId")
        if not ingredient_id:
            continue
        
        qty = record.get("qty", 0)
        unit_cost = record.get("unitCost", 0)
        
        if ingredient_id not in valuation_data:
            valuation_data[ingredient_id] = {
                "totalQty": 0,
                "totalValue": 0,
                "transactions": []
            }
        
        valuation_data[ingredient_id]["totalQty"] += qty
        valuation_data[ingredient_id]["totalValue"] += qty * unit_cost
        valuation_data[ingredient_id]["transactions"].append({
            "qty": qty,
            "unitCost": unit_cost,
            "date": record.get("createdAt")
        })
    
    # Build result with weighted average cost
    result = []
    for ingredient_id, data in valuation_data.items():
        ingredient = ingredient_map.get(ingredient_id)
        if not ingredient:
            continue
        
        weighted_avg_cost = data["totalValue"] / data["totalQty"] if data["totalQty"] > 0 else 0
        
        result.append({
            "ingredientId": ingredient_id,
            "ingredientName": ingredient["name"],
            "category": ingredient.get("category", "food"),
            "unit": ingredient["unit"],
            "totalQty": data["totalQty"],
            "weightedAvgCost": weighted_avg_cost,
            "totalValue": data["totalValue"],
            "transactionCount": len(data["transactions"])
        })
    
    return result

@api_router.get("/inventory/valuation/summary")
async def get_inventory_valuation_summary(current_user: dict = Depends(get_current_user)):
    """Get valuation summary by category and overall total"""
    await check_subscription(current_user)
    
    # Get per-item valuation
    valuation = await get_inventory_valuation(current_user)
    
    # Aggregate by category
    category_totals = {
        "food": 0,
        "beverage": 0,
        "nofood": 0
    }
    
    for item in valuation:
        category = item.get("category", "food")
        if category in category_totals:
            category_totals[category] += item["totalValue"]
    
    overall_total = sum(category_totals.values())
    
    return {
        "categories": {
            "food": category_totals["food"],
            "beverage": category_totals["beverage"],
            "nofood": category_totals["nofood"]
        },
        "total": overall_total,
        "itemCount": len(valuation)
    }

@api_router.post("/inventory/adjustments")
async def create_inventory_adjustment(
    adjustment: dict,
    current_user: dict = Depends(get_current_user)
):
    """Create manual inventory adjustment (admin only)"""
    await check_subscription(current_user)
    
    # RBAC check - admin only
    if current_user.get("role") != "admin" and current_user.get("roleKey") != "administrator":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    ingredient_id = adjustment.get("ingredientId")
    qty_adjustment = adjustment.get("qtyAdjustment", 0)
    reason = adjustment.get("reason", "")
    
    if not ingredient_id or not reason:
        raise HTTPException(status_code=400, detail="ingredientId and reason are required")
    
    # Validate ingredient exists
    ingredient = await db.ingredients.find_one(
        {"id": ingredient_id, "restaurantId": current_user["restaurantId"]}
    )
    
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    
    # Create adjustment record
    adjustment_record = {
        "id": str(uuid.uuid4()),
        "restaurantId": current_user["restaurantId"],
        "ingredientId": ingredient_id,
        "ingredientName": ingredient["name"],
        "qtyAdjustment": qty_adjustment,
        "unit": ingredient["unit"],
        "reason": reason,
        "adjustedBy": current_user["id"],
        "adjustedByName": current_user.get("displayName", "Unknown"),
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.inventory_adjustments.insert_one(adjustment_record)
    
    # Create corresponding inventory record
    if qty_adjustment != 0:
        inventory_record = {
            "id": str(uuid.uuid4()),
            "restaurantId": current_user["restaurantId"],
            "ingredientId": ingredient_id,
            "qty": qty_adjustment,
            "unit": ingredient["unit"],
            "countType": "adjustment",
            "batchExpiry": None,
            "location": f"Manual adjustment by {current_user.get('displayName')}",
            "adjustmentId": adjustment_record["id"],
            "createdAt": datetime.now(timezone.utc).isoformat()
        }
        
        await db.inventory.insert_one(inventory_record)
    
    # Log audit
    await log_audit(
        db,
        current_user["restaurantId"],
        current_user["id"],
        "adjustment",
        "inventory",
        adjustment_record["id"],
        {
            "ingredient": ingredient["name"],
            "qtyAdjustment": qty_adjustment,
            "reason": reason
        }
    )
    
    adjustment_record.pop("_id", None)
    return adjustment_record

@api_router.get("/inventory/adjustments")
async def get_inventory_adjustments(current_user: dict = Depends(get_current_user)):
    """Get all inventory adjustments"""
    await check_subscription(current_user)
    
    adjustments = await db.inventory_adjustments.find(
        {"restaurantId": current_user["restaurantId"]},
        {"_id": 0}
    ).sort("createdAt", -1).to_list(1000)
    
    return adjustments

# ============ RECIPES ROUTES ============

@api_router.post("/recipes", response_model=Recipe)
async def create_recipe(recipe_data: RecipeCreate, current_user: dict = Depends(get_current_user)):
    await check_subscription(current_user)
    
    # Validate non-empty items array
    if not recipe_data.items or len(recipe_data.items) == 0:
        raise HTTPException(status_code=422, detail="Recipe must have at least one item")
    
    # Validate all items exist
    for item in recipe_data.items:
        if item.type == 'ingredient':
            ingredient = await db.ingredients.find_one(
                {"id": item.itemId, "restaurantId": current_user["restaurantId"]}
            )
            if not ingredient:
                raise HTTPException(status_code=404, detail=f"Ingredient {item.itemId} not found")
        elif item.type == 'preparation':
            preparation = await db.preparations.find_one(
                {"id": item.itemId, "restaurantId": current_user["restaurantId"]}
            )
            if not preparation:
                raise HTTPException(status_code=404, detail=f"Preparation {item.itemId} not found")
        else:
            raise HTTPException(status_code=422, detail=f"Invalid item type: {item.type}")
    
    # Compute allergens from all items
    items_dict = [item.dict() for item in recipe_data.items]
    allergens = await compute_recipe_allergens(items_dict, db)
    
    recipe_id = str(uuid.uuid4())
    recipe = {
        "id": recipe_id,
        "restaurantId": current_user["restaurantId"],
        "name": recipe_data.name,
        "category": recipe_data.category,
        "portions": recipe_data.portions,
        "targetFoodCostPct": recipe_data.targetFoodCostPct,
        "price": recipe_data.price,
        "items": items_dict,
        "allergens": allergens,
        "shelfLife": recipe_data.shelfLife.dict() if recipe_data.shelfLife else None,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "updatedAt": None
    }
    
    await db.recipes.insert_one(recipe)
    recipe.pop("_id", None)
    return Recipe(**recipe)

@api_router.get("/recipes", response_model=List[Recipe])
async def get_recipes(current_user: dict = Depends(get_current_user)):
    await check_subscription(current_user)
    recipes = await db.recipes.find({"restaurantId": current_user["restaurantId"]}, {"_id": 0}).to_list(1000)
    return [Recipe(**rec) for rec in recipes]

@api_router.get("/recipes/{recipe_id}", response_model=Recipe)
async def get_recipe(recipe_id: str, current_user: dict = Depends(get_current_user)):
    recipe = await db.recipes.find_one({"id": recipe_id, "restaurantId": current_user["restaurantId"]}, {"_id": 0})
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return Recipe(**recipe)

@api_router.put("/recipes/{recipe_id}", response_model=Recipe)
async def update_recipe(recipe_id: str, recipe_data: RecipeUpdate, current_user: dict = Depends(get_current_user)):
    await check_subscription(current_user)
    
    # Check if recipe exists
    existing = await db.recipes.find_one(
        {"id": recipe_id, "restaurantId": current_user["restaurantId"]}
    )
    
    if not existing:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    # Build update data
    update_data = {}
    
    if recipe_data.name is not None:
        update_data["name"] = recipe_data.name
    
    if recipe_data.category is not None:
        update_data["category"] = recipe_data.category
    
    if recipe_data.portions is not None:
        update_data["portions"] = recipe_data.portions
    
    if recipe_data.targetFoodCostPct is not None:
        update_data["targetFoodCostPct"] = recipe_data.targetFoodCostPct
    
    if recipe_data.price is not None:
        update_data["price"] = recipe_data.price
    
    if recipe_data.items is not None:
        items_dict = [item.dict() for item in recipe_data.items]
        update_data["items"] = items_dict
        # Recompute allergens when items change
        allergens = await compute_recipe_allergens(items_dict, db)
        update_data["allergens"] = allergens
    
    if recipe_data.shelfLife is not None:
        update_data["shelfLife"] = recipe_data.shelfLife.dict()
    
    update_data["updatedAt"] = datetime.now(timezone.utc).isoformat()
    
    # Update in database
    await db.recipes.update_one(
        {"id": recipe_id},
        {"$set": update_data}
    )
    
    # Get updated recipe
    updated_recipe = await db.recipes.find_one(
        {"id": recipe_id},
        {"_id": 0}
    )
    
    return Recipe(**updated_recipe)
    
    existing = await db.recipes.find_one({"id": recipe_id, "restaurantId": current_user["restaurantId"]})
    if not existing:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    update_data = {
        "name": recipe_data.name,
        "category": recipe_data.category,
        "portions": recipe_data.portions,
        "targetFoodCostPct": recipe_data.targetFoodCostPct,
        "price": recipe_data.price,
        "items": [item.model_dump() for item in recipe_data.items]
    }
    
    await db.recipes.update_one({"id": recipe_id}, {"$set": update_data})
    updated = await db.recipes.find_one({"id": recipe_id}, {"_id": 0})
    return Recipe(**updated)

@api_router.delete("/recipes/{recipe_id}")
async def delete_recipe(recipe_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.recipes.delete_one({"id": recipe_id, "restaurantId": current_user["restaurantId"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    return {"message": "Recipe deleted"}

# ============ SALES ROUTES ============

@api_router.post("/sales", response_model=Sales)
async def create_sales(sales_data: SalesCreate, current_user: dict = Depends(get_current_user)):
    await check_subscription(current_user)
    
    sales_id = str(uuid.uuid4())
    sales = {
        "id": sales_id,
        "restaurantId": current_user["restaurantId"],
        "date": sales_data.date,
        "lines": [line.model_dump() for line in sales_data.lines],
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.sales.insert_one(sales)
    return Sales(**sales)

@api_router.get("/sales", response_model=List[Sales])
async def get_sales(current_user: dict = Depends(get_current_user)):
    await check_subscription(current_user)
    sales = await db.sales.find({"restaurantId": current_user["restaurantId"]}, {"_id": 0}).to_list(1000)
    return [Sales(**s) for s in sales]

@api_router.delete("/sales/{sales_id}")
async def delete_sales(sales_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.sales.delete_one({"id": sales_id, "restaurantId": current_user["restaurantId"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Sales record not found")
    
    return {"message": "Sales deleted"}

# ============ WASTAGE ROUTES ============

@api_router.post("/wastage", response_model=Wastage)
async def create_wastage(wastage_data: WastageCreate, current_user: dict = Depends(get_current_user)):
    await check_subscription(current_user)
    
    wastage_id = str(uuid.uuid4())
    wastage = {
        "id": wastage_id,
        "restaurantId": current_user["restaurantId"],
        "date": wastage_data.date,
        "type": wastage_data.type,
        "ingredientId": wastage_data.ingredientId,
        "recipeId": wastage_data.recipeId,
        "qty": wastage_data.qty,
        "unit": wastage_data.unit,
        "reason": wastage_data.reason,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.wastage.insert_one(wastage)
    return Wastage(**wastage)

@api_router.get("/wastage", response_model=List[Wastage])
async def get_wastage(current_user: dict = Depends(get_current_user)):
    await check_subscription(current_user)
    wastage = await db.wastage.find({"restaurantId": current_user["restaurantId"]}, {"_id": 0}).to_list(1000)
    return [Wastage(**w) for w in wastage]

@api_router.delete("/wastage/{wastage_id}")
async def delete_wastage(wastage_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.wastage.delete_one({"id": wastage_id, "restaurantId": current_user["restaurantId"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Wastage record not found")
    
    return {"message": "Wastage deleted"}

# ============ P&L ROUTES ============

@api_router.post("/pl", response_model=PL)
async def create_pl(pl_data: PLCreate, current_user: dict = Depends(get_current_user)):
    await check_subscription(current_user)
    
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    pl_id = str(uuid.uuid4())
    pl = {
        "id": pl_id,
        "restaurantId": current_user["restaurantId"],
        "month": pl_data.month,
        "revenue": pl_data.revenue,
        "cogs": pl_data.cogs,
        "grossMargin": pl_data.grossMargin,
        "notes": pl_data.notes,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.pl.insert_one(pl)
    return PL(**pl)

@api_router.get("/pl", response_model=List[PL])
async def get_pl(current_user: dict = Depends(get_current_user)):
    await check_subscription(current_user)
    pl = await db.pl.find({"restaurantId": current_user["restaurantId"]}, {"_id": 0}).to_list(1000)
    return [PL(**p) for p in pl]

@api_router.delete("/pl/{pl_id}")
async def delete_pl(pl_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.pl.delete_one({"id": pl_id, "restaurantId": current_user["restaurantId"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="P&L record not found")
    
    return {"message": "P&L deleted"}

# ============ FILE UPLOAD & DOWNLOAD ============

from fastapi import File, UploadFile
from fastapi.responses import Response

@api_router.post("/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    subfolder: str = "general",
    current_user: dict = Depends(get_current_user)
):
    """Upload a file with validation"""
    await check_subscription(current_user)
    
    try:
        # Read file content
        file_data = await file.read()
        
        # Get storage service and save file
        storage = get_storage_service()
        file_metadata = await storage.save_file(file_data, file.filename, subfolder)
        
        # Save metadata to database
        file_record = {
            "id": str(uuid.uuid4()),
            "restaurantId": current_user["restaurantId"],
            "filename": file_metadata["filename"],
            "path": file_metadata["path"],
            "size": file_metadata["size"],
            "mimeType": file_metadata["mime_type"],
            "hash": file_metadata["hash"],
            "uploadedBy": current_user["id"],
            "uploadedAt": datetime.now(timezone.utc).isoformat()
        }
        
        await db.files.insert_one(file_record)
        
        # Log audit
        await log_audit(
            db,
            current_user["restaurantId"],
            current_user["id"],
            "upload",
            "file",
            file_record["id"],
            {"filename": file.filename, "size": file_metadata["size"]}
        )
        
        # Return without _id
        file_record.pop("_id", None)
        return file_record
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"File upload error: {str(e)}")
        raise HTTPException(status_code=500, detail="File upload failed")

@api_router.get("/files/{file_id}")
async def download_file(
    file_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Download a file with authentication and tenant check"""
    await check_subscription(current_user)
    
    # Get file metadata from database
    file_record = await db.files.find_one(
        {"id": file_id, "restaurantId": current_user["restaurantId"]},
        {"_id": 0}
    )
    
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        # Read file from storage
        storage = get_storage_service()
        file_data = await storage.read_file(file_record["path"])
        
        # Return file with appropriate headers
        return Response(
            content=file_data,
            media_type=file_record["mimeType"],
            headers={
                "Content-Disposition": f'attachment; filename="{file_record["filename"]}"'
            }
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found in storage")
    except Exception as e:
        logger.error(f"File download error: {str(e)}")
        raise HTTPException(status_code=500, detail="File download failed")

@api_router.delete("/files/{file_id}")
async def delete_file(
    file_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a file"""
    await check_subscription(current_user)
    
    # Get file metadata
    file_record = await db.files.find_one(
        {"id": file_id, "restaurantId": current_user["restaurantId"]},
        {"_id": 0}
    )
    
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        # Delete from storage
        storage = get_storage_service()
        await storage.delete_file(file_record["path"])
        
        # Delete from database
        await db.files.delete_one({"id": file_id})
        
        # Log audit
        await log_audit(
            db,
            current_user["restaurantId"],
            current_user["id"],
            "delete",
            "file",
            file_id,
            {"filename": file_record["filename"]}
        )
        
        return {"message": "File deleted"}
    except Exception as e:
        logger.error(f"File delete error: {str(e)}")
        raise HTTPException(status_code=500, detail="File delete failed")

# ============ SUPPLIERS ============

@api_router.post("/suppliers", response_model=Supplier)
async def create_supplier(supplier: SupplierCreate, current_user: dict = Depends(get_current_user)):
    """Create a new supplier"""
    await check_subscription(current_user)
    
    supplier_data = {
        "id": str(uuid.uuid4()),
        "restaurantId": current_user["restaurantId"],
        "name": supplier.name,
        "contacts": supplier.contacts.dict() if supplier.contacts else None,
        "notes": supplier.notes,
        "files": [],
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "updatedAt": None
    }
    
    await db.suppliers.insert_one(supplier_data)
    
    # Log audit
    await log_audit(
        db,
        current_user["restaurantId"],
        current_user["id"],
        "create",
        "supplier",
        supplier_data["id"],
        {"name": supplier.name}
    )
    
    supplier_data.pop("_id", None)
    return Supplier(**supplier_data)

@api_router.get("/suppliers", response_model=List[Supplier])
async def get_suppliers(current_user: dict = Depends(get_current_user)):
    """Get all suppliers for the restaurant"""
    await check_subscription(current_user)
    
    suppliers = await db.suppliers.find(
        {"restaurantId": current_user["restaurantId"]},
        {"_id": 0}
    ).to_list(1000)
    
    return [Supplier(**s) for s in suppliers]

@api_router.get("/suppliers/{supplier_id}", response_model=Supplier)
async def get_supplier(supplier_id: str, current_user: dict = Depends(get_current_user)):
    """Get a specific supplier"""
    await check_subscription(current_user)
    
    supplier = await db.suppliers.find_one(
        {"id": supplier_id, "restaurantId": current_user["restaurantId"]},
        {"_id": 0}
    )
    
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    return Supplier(**supplier)

@api_router.put("/suppliers/{supplier_id}", response_model=Supplier)
async def update_supplier(
    supplier_id: str,
    supplier_update: SupplierUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a supplier"""
    await check_subscription(current_user)
    
    # Check if supplier exists
    existing = await db.suppliers.find_one(
        {"id": supplier_id, "restaurantId": current_user["restaurantId"]}
    )
    
    if not existing:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    # Build update data
    update_data = {}
    if supplier_update.name is not None:
        update_data["name"] = supplier_update.name
    if supplier_update.contacts is not None:
        update_data["contacts"] = supplier_update.contacts.dict()
    if supplier_update.notes is not None:
        update_data["notes"] = supplier_update.notes
    
    update_data["updatedAt"] = datetime.now(timezone.utc).isoformat()
    
    # Update in database
    await db.suppliers.update_one(
        {"id": supplier_id},
        {"$set": update_data}
    )
    
    # Log audit
    await log_audit(
        db,
        current_user["restaurantId"],
        current_user["id"],
        "update",
        "supplier",
        supplier_id,
        update_data
    )
    
    # Get updated supplier
    updated_supplier = await db.suppliers.find_one(
        {"id": supplier_id},
        {"_id": 0}
    )
    
    return Supplier(**updated_supplier)

@api_router.delete("/suppliers/{supplier_id}")
async def delete_supplier(supplier_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a supplier"""
    await check_subscription(current_user)
    
    # Check if supplier exists
    supplier = await db.suppliers.find_one(
        {"id": supplier_id, "restaurantId": current_user["restaurantId"]},
        {"_id": 0}
    )
    
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    # Delete associated files
    storage = get_storage_service()
    for file_meta in supplier.get("files", []):
        try:
            await storage.delete_file(file_meta["path"])
            await db.files.delete_one({"id": file_meta["id"]})
        except Exception as e:
            logger.warning(f"Error deleting file {file_meta['id']}: {str(e)}")
    
    # Delete supplier
    await db.suppliers.delete_one({"id": supplier_id})
    
    # Log audit
    await log_audit(
        db,
        current_user["restaurantId"],
        current_user["id"],
        "delete",
        "supplier",
        supplier_id,
        {"name": supplier["name"]}
    )
    
    return {"message": "Supplier deleted"}

@api_router.post("/suppliers/{supplier_id}/files")
async def attach_file_to_supplier(
    supplier_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Attach a file to a supplier"""
    await check_subscription(current_user)
    
    # Check if supplier exists
    supplier = await db.suppliers.find_one(
        {"id": supplier_id, "restaurantId": current_user["restaurantId"]}
    )
    
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    try:
        # Upload file
        file_data = await file.read()
        storage = get_storage_service()
        file_metadata = await storage.save_file(file_data, file.filename, f"suppliers/{supplier_id}")
        
        # Save file metadata to database
        file_record = {
            "id": str(uuid.uuid4()),
            "restaurantId": current_user["restaurantId"],
            "filename": file_metadata["filename"],
            "path": file_metadata["path"],
            "size": file_metadata["size"],
            "mimeType": file_metadata["mime_type"],
            "hash": file_metadata["hash"],
            "uploadedBy": current_user["id"],
            "uploadedAt": datetime.now(timezone.utc).isoformat()
        }
        
        await db.files.insert_one(file_record)
        
        # Add file reference to supplier
        file_record.pop("_id", None)
        await db.suppliers.update_one(
            {"id": supplier_id},
            {"$push": {"files": file_record}}
        )
        
        # Log audit
        await log_audit(
            db,
            current_user["restaurantId"],
            current_user["id"],
            "attach_file",
            "supplier",
            supplier_id,
            {"filename": file.filename}
        )
        
        return file_record
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"File attachment error: {str(e)}")
        raise HTTPException(status_code=500, detail="File attachment failed")

@api_router.delete("/suppliers/{supplier_id}/files/{file_id}")
async def detach_file_from_supplier(
    supplier_id: str,
    file_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Detach a file from a supplier"""
    await check_subscription(current_user)
    
    # Check if supplier exists
    supplier = await db.suppliers.find_one(
        {"id": supplier_id, "restaurantId": current_user["restaurantId"]},
        {"_id": 0}
    )
    
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    # Find the file in supplier's files
    file_to_remove = None
    for f in supplier.get("files", []):
        if f["id"] == file_id:
            file_to_remove = f
            break
    
    if not file_to_remove:
        raise HTTPException(status_code=404, detail="File not found in supplier")
    
    try:
        # Delete from storage
        storage = get_storage_service()
        await storage.delete_file(file_to_remove["path"])
        
        # Delete from files collection
        await db.files.delete_one({"id": file_id})
        
        # Remove from supplier's files array
        await db.suppliers.update_one(
            {"id": supplier_id},
            {"$pull": {"files": {"id": file_id}}}
        )
        
        # Log audit
        await log_audit(
            db,
            current_user["restaurantId"],
            current_user["id"],
            "detach_file",
            "supplier",
            supplier_id,
            {"filename": file_to_remove["filename"]}
        )
        
        return {"message": "File detached"}
    
    except Exception as e:
        logger.error(f"File detach error: {str(e)}")
        raise HTTPException(status_code=500, detail="File detach failed")

# ============ RECEIVING (Goods In) ============

@api_router.post("/receiving", response_model=Receiving)
async def create_receiving(receiving: ReceivingCreate, current_user: dict = Depends(get_current_user)):
    """Create a new receiving record and update inventory"""
    await check_subscription(current_user)
    
    # Validate supplier exists
    supplier = await db.suppliers.find_one(
        {"id": receiving.supplierId, "restaurantId": current_user["restaurantId"]}
    )
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    # Validate category
    if receiving.category not in ['food', 'beverage', 'nofood']:
        raise HTTPException(status_code=400, detail="Invalid category. Must be: food, beverage, or nofood")
    
    # Calculate total
    total = sum(line.qty * line.unitPrice for line in receiving.lines)
    
    # Create receiving record
    receiving_data = {
        "id": str(uuid.uuid4()),
        "restaurantId": current_user["restaurantId"],
        "supplierId": receiving.supplierId,
        "category": receiving.category,
        "lines": [line.dict() for line in receiving.lines],
        "total": total,
        "files": [],
        "arrivedAt": receiving.arrivedAt,
        "notes": receiving.notes,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "updatedAt": None
    }
    
    await db.receiving.insert_one(receiving_data)
    
    # Write-through to Inventory (add quantities)
    for line in receiving.lines:
        if line.ingredientId:
            # Check if ingredient exists
            ingredient = await db.ingredients.find_one(
                {"id": line.ingredientId, "restaurantId": current_user["restaurantId"]}
            )
            
            if ingredient:
                # Create inventory record for received goods
                inventory_record = {
                    "id": str(uuid.uuid4()),
                    "restaurantId": current_user["restaurantId"],
                    "ingredientId": line.ingredientId,
                    "qty": line.qty,
                    "unit": line.unit,
                    "countType": "receiving",
                    "batchExpiry": line.expiryDate,
                    "location": f"Receiving from {supplier['name']}",
                    "receivingId": receiving_data["id"],
                    "unitCost": line.unitPrice,  # Store unit cost for valuation
                    "createdAt": datetime.now(timezone.utc).isoformat()
                }
                
                await db.inventory.insert_one(inventory_record)
    
    # Log audit
    await log_audit(
        db,
        current_user["restaurantId"],
        current_user["id"],
        "create",
        "receiving",
        receiving_data["id"],
        {"supplier": supplier["name"], "category": receiving.category, "total": total}
    )
    
    receiving_data.pop("_id", None)
    return Receiving(**receiving_data)

@api_router.get("/receiving", response_model=List[Receiving])
async def get_receiving(current_user: dict = Depends(get_current_user)):
    """Get all receiving records for the restaurant"""
    await check_subscription(current_user)
    
    receiving_records = await db.receiving.find(
        {"restaurantId": current_user["restaurantId"]},
        {"_id": 0}
    ).sort("arrivedAt", -1).to_list(1000)
    
    return [Receiving(**r) for r in receiving_records]

@api_router.get("/receiving/{receiving_id}", response_model=Receiving)
async def get_receiving_by_id(receiving_id: str, current_user: dict = Depends(get_current_user)):
    """Get a specific receiving record"""
    await check_subscription(current_user)
    
    receiving = await db.receiving.find_one(
        {"id": receiving_id, "restaurantId": current_user["restaurantId"]},
        {"_id": 0}
    )
    
    if not receiving:
        raise HTTPException(status_code=404, detail="Receiving record not found")
    
    return Receiving(**receiving)

@api_router.put("/receiving/{receiving_id}", response_model=Receiving)
async def update_receiving(
    receiving_id: str,
    receiving_update: ReceivingUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a receiving record"""
    await check_subscription(current_user)
    
    # Check if receiving exists
    existing = await db.receiving.find_one(
        {"id": receiving_id, "restaurantId": current_user["restaurantId"]}
    )
    
    if not existing:
        raise HTTPException(status_code=404, detail="Receiving record not found")
    
    # Build update data
    update_data = {}
    
    if receiving_update.supplierId is not None:
        # Validate supplier
        supplier = await db.suppliers.find_one(
            {"id": receiving_update.supplierId, "restaurantId": current_user["restaurantId"]}
        )
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")
        update_data["supplierId"] = receiving_update.supplierId
    
    if receiving_update.category is not None:
        if receiving_update.category not in ['food', 'beverage', 'nofood']:
            raise HTTPException(status_code=400, detail="Invalid category")
        update_data["category"] = receiving_update.category
    
    if receiving_update.lines is not None:
        update_data["lines"] = [line.dict() for line in receiving_update.lines]
        # Recalculate total
        update_data["total"] = sum(line.qty * line.unitPrice for line in receiving_update.lines)
    
    if receiving_update.arrivedAt is not None:
        update_data["arrivedAt"] = receiving_update.arrivedAt
    
    if receiving_update.notes is not None:
        update_data["notes"] = receiving_update.notes
    
    update_data["updatedAt"] = datetime.now(timezone.utc).isoformat()
    
    # Update in database
    await db.receiving.update_one(
        {"id": receiving_id},
        {"$set": update_data}
    )
    
    # Log audit
    await log_audit(
        db,
        current_user["restaurantId"],
        current_user["id"],
        "update",
        "receiving",
        receiving_id,
        update_data
    )
    
    # Get updated receiving
    updated_receiving = await db.receiving.find_one(
        {"id": receiving_id},
        {"_id": 0}
    )
    
    return Receiving(**updated_receiving)

@api_router.delete("/receiving/{receiving_id}")
async def delete_receiving(receiving_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a receiving record"""
    await check_subscription(current_user)
    
    # Check if receiving exists
    receiving = await db.receiving.find_one(
        {"id": receiving_id, "restaurantId": current_user["restaurantId"]},
        {"_id": 0}
    )
    
    if not receiving:
        raise HTTPException(status_code=404, detail="Receiving record not found")
    
    # Delete associated inventory records
    await db.inventory.delete_many({"receivingId": receiving_id})
    
    # Delete associated files
    storage = get_storage_service()
    for file_meta in receiving.get("files", []):
        try:
            await storage.delete_file(file_meta["path"])
            await db.files.delete_one({"id": file_meta["id"]})
        except Exception as e:
            logger.warning(f"Error deleting file {file_meta['id']}: {str(e)}")
    
    # Delete receiving
    await db.receiving.delete_one({"id": receiving_id})
    
    # Log audit
    await log_audit(
        db,
        current_user["restaurantId"],
        current_user["id"],
        "delete",
        "receiving",
        receiving_id,
        {"category": receiving["category"], "total": receiving["total"]}
    )
    
    return {"message": "Receiving record deleted"}

@api_router.post("/receiving/{receiving_id}/files")
async def attach_file_to_receiving(
    receiving_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Attach a file to a receiving record"""
    await check_subscription(current_user)
    
    # Check if receiving exists
    receiving = await db.receiving.find_one(
        {"id": receiving_id, "restaurantId": current_user["restaurantId"]}
    )
    
    if not receiving:
        raise HTTPException(status_code=404, detail="Receiving record not found")
    
    try:
        # Upload file
        file_data = await file.read()
        storage = get_storage_service()
        file_metadata = await storage.save_file(file_data, file.filename, f"receiving/{receiving_id}")
        
        # Save file metadata to database
        file_record = {
            "id": str(uuid.uuid4()),
            "restaurantId": current_user["restaurantId"],
            "filename": file_metadata["filename"],
            "path": file_metadata["path"],
            "size": file_metadata["size"],
            "mimeType": file_metadata["mime_type"],
            "hash": file_metadata["hash"],
            "uploadedBy": current_user["id"],
            "uploadedAt": datetime.now(timezone.utc).isoformat()
        }
        
        await db.files.insert_one(file_record)
        
        # Add file reference to receiving
        file_record.pop("_id", None)
        await db.receiving.update_one(
            {"id": receiving_id},
            {"$push": {"files": file_record}}
        )
        
        # Log audit
        await log_audit(
            db,
            current_user["restaurantId"],
            current_user["id"],
            "attach_file",
            "receiving",
            receiving_id,
            {"filename": file.filename}
        )
        
        return file_record
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"File attachment error: {str(e)}")
        raise HTTPException(status_code=500, detail="File attachment failed")

@api_router.delete("/receiving/{receiving_id}/files/{file_id}")
async def detach_file_from_receiving(
    receiving_id: str,
    file_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Detach a file from a receiving record"""
    await check_subscription(current_user)
    
    # Check if receiving exists
    receiving = await db.receiving.find_one(
        {"id": receiving_id, "restaurantId": current_user["restaurantId"]},
        {"_id": 0}
    )
    
    if not receiving:
        raise HTTPException(status_code=404, detail="Receiving record not found")
    
    # Find the file in receiving's files
    file_to_remove = None
    for f in receiving.get("files", []):
        if f["id"] == file_id:
            file_to_remove = f
            break
    
    if not file_to_remove:
        raise HTTPException(status_code=404, detail="File not found in receiving record")
    
    try:
        # Delete from storage
        storage = get_storage_service()
        await storage.delete_file(file_to_remove["path"])
        
        # Delete from files collection
        await db.files.delete_one({"id": file_id})
        
        # Remove from receiving's files array
        await db.receiving.update_one(
            {"id": receiving_id},
            {"$pull": {"files": {"id": file_id}}}
        )
        
        # Log audit
        await log_audit(
            db,
            current_user["restaurantId"],
            current_user["id"],
            "detach_file",
            "receiving",
            receiving_id,
            {"filename": file_to_remove["filename"]}
        )
        
        return {"message": "File detached"}
    
    except Exception as e:
        logger.error(f"File detach error: {str(e)}")
        raise HTTPException(status_code=500, detail="File detach failed")

# ============ DASHBOARD KPIs ============

@api_router.get("/dashboard/kpis")
async def get_dashboard_kpis(current_user: dict = Depends(get_current_user)):
    await check_subscription(current_user)
    
    restaurant_id = current_user["restaurantId"]
    
    # Get all data needed for KPIs
    ingredients = await db.ingredients.find({"restaurantId": restaurant_id}, {"_id": 0}).to_list(1000)
    inventory = await db.inventory.find({"restaurantId": restaurant_id}, {"_id": 0}).to_list(1000)
    recipes = await db.recipes.find({"restaurantId": restaurant_id}, {"_id": 0}).to_list(1000)
    sales = await db.sales.find({"restaurantId": restaurant_id}, {"_id": 0}).to_list(1000)
    
    # Calculate food cost %
    total_revenue = 0
    total_cogs = 0
    
    ingredients_map = {ing["id"]: ing for ing in ingredients}
    recipes_map = {rec["id"]: rec for rec in recipes}
    
    for sale in sales:
        for line in sale.get("lines", []):
            recipe = recipes_map.get(line["recipeId"])
            if recipe:
                qty = line["qty"]
                total_revenue += recipe["price"] * qty
                
                # Calculate recipe cost
                recipe_cost = 0
                for item in recipe.get("items", []):
                    ingredient = ingredients_map.get(item["ingredientId"])
                    if ingredient:
                        recipe_cost += ingredient["unitCost"] * item["qtyPerPortion"]
                
                total_cogs += recipe_cost * qty
    
    food_cost_pct = (total_cogs / total_revenue * 100) if total_revenue > 0 else 0
    
    # Low stock items
    inventory_agg = {}
    for inv in inventory:
        ingredient_id = inv["ingredientId"]
        if ingredient_id not in inventory_agg:
            inventory_agg[ingredient_id] = 0
        
        if inv["countType"] == "opening" or inv["countType"] == "adjustment":
            inventory_agg[ingredient_id] += inv["qty"]
        elif inv["countType"] == "closing":
            inventory_agg[ingredient_id] = inv["qty"]
    
    low_stock_count = 0
    for ing in ingredients:
        current_qty = inventory_agg.get(ing["id"], 0)
        if current_qty < ing.get("minStockQty", 0):
            low_stock_count += 1
    
    # Expiring items
    now = datetime.now(timezone.utc)
    expiring_1day = 0
    expiring_2day = 0
    expiring_3day = 0
    
    for inv in inventory:
        if inv.get("batchExpiry"):
            try:
                expiry_date = datetime.fromisoformat(inv["batchExpiry"].replace('Z', '+00:00'))
                days_until = (expiry_date - now).days
                
                if days_until <= 1 and days_until >= 0:
                    expiring_1day += 1
                elif days_until <= 2:
                    expiring_2day += 1
                elif days_until <= 3:
                    expiring_3day += 1
            except Exception:
                pass
    
    # Last month P&L
    pl_records = await db.pl.find({"restaurantId": restaurant_id}, {"_id": 0}).sort("month", -1).limit(1).to_list(1)
    last_month_gm = pl_records[0]["grossMargin"] if pl_records else 0
    
    return {
        "foodCostPct": round(food_cost_pct, 2),
        "lowStockCount": low_stock_count,
        "expiring1Day": expiring_1day,
        "expiring2Day": expiring_2day,
        "expiring3Day": expiring_3day,
        "lastMonthGrossMargin": round(last_month_gm, 2),
        "totalRevenue": round(total_revenue, 2),
        "totalCogs": round(total_cogs, 2)
    }

# ============ RESTAURANT ROUTES ============

@api_router.get("/restaurant")
async def get_restaurant(current_user: dict = Depends(get_current_user)):
    restaurant = await db.restaurants.find_one({"id": current_user["restaurantId"]}, {"_id": 0})
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return restaurant

@api_router.put("/restaurant")
async def update_restaurant(data: dict, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    allowed_fields = ["name", "plan"]
    update_data = {k: v for k, v in data.items() if k in allowed_fields}
    
    if update_data:
        await db.restaurants.update_one(
            {"id": current_user["restaurantId"]},
            {"$set": update_data}
        )
    
    restaurant = await db.restaurants.find_one({"id": current_user["restaurantId"]}, {"_id": 0})
    return restaurant

# Include the router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()