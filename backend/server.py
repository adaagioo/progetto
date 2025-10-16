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

class IngredientCreate(BaseModel):
    name: str
    unit: str
    packSize: float
    packCost: float
    supplier: Optional[str] = None
    allergen: Optional[str] = None
    minStockQty: float = 0

class Ingredient(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    restaurantId: str
    name: str
    unit: str
    packSize: float
    packCost: float
    unitCost: float
    supplier: Optional[str] = None
    allergen: Optional[str] = None
    minStockQty: float
    createdAt: str

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
    ingredientId: str
    qtyPerPortion: float
    unit: str

class RecipeCreate(BaseModel):
    name: str
    category: str
    portions: int
    targetFoodCostPct: float
    price: float
    items: List[RecipeItem]

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
    createdAt: str

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

# ============ AUTH HELPERS ============

async def send_email(to_email: str, subject: str, body: str):
    """Send email via SMTP or log to console if SMTP not configured"""
    if not SMTP_HOST or not SMTP_USER:
        logger.info(f"\n{'='*60}\nEmail Mock (SMTP not configured)\nTo: {to_email}\nSubject: {subject}\n{body}\n{'='*60}\n")
        return True
    
    try:
        message = MIMEMultipart()
        message['From'] = MAIL_FROM
        message['To'] = to_email
        message['Subject'] = subject
        message.attach(MIMEText(body, 'plain'))
        
        await aiosmtplib.send(
            message,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASS,
            start_tls=True
        )
        logger.info(f"Email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return False

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
        "role": user["role"]
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
    
    ingredient = {
        "id": ingredient_id,
        "restaurantId": current_user["restaurantId"],
        "name": ingredient_data.name,
        "unit": ingredient_data.unit,
        "packSize": ingredient_data.packSize,
        "packCost": ingredient_data.packCost,
        "unitCost": unit_cost,
        "supplier": ingredient_data.supplier,
        "allergen": ingredient_data.allergen,
        "minStockQty": ingredient_data.minStockQty,
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
    
    update_data = {
        "name": ingredient_data.name,
        "unit": ingredient_data.unit,
        "packSize": ingredient_data.packSize,
        "packCost": ingredient_data.packCost,
        "unitCost": unit_cost,
        "supplier": ingredient_data.supplier,
        "allergen": ingredient_data.allergen,
        "minStockQty": ingredient_data.minStockQty
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

# ============ RECIPES ROUTES ============

@api_router.post("/recipes", response_model=Recipe)
async def create_recipe(recipe_data: RecipeCreate, current_user: dict = Depends(get_current_user)):
    await check_subscription(current_user)
    
    recipe_id = str(uuid.uuid4())
    recipe = {
        "id": recipe_id,
        "restaurantId": current_user["restaurantId"],
        "name": recipe_data.name,
        "category": recipe_data.category,
        "portions": recipe_data.portions,
        "targetFoodCostPct": recipe_data.targetFoodCostPct,
        "price": recipe_data.price,
        "items": [item.model_dump() for item in recipe_data.items],
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.recipes.insert_one(recipe)
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
async def update_recipe(recipe_id: str, recipe_data: RecipeCreate, current_user: dict = Depends(get_current_user)):
    await check_subscription(current_user)
    
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
            except:
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