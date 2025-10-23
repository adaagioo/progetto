from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr, field_validator
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt
import hashlib
import secrets
import aiosmtplib
from passlib.context import CryptContext
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

# Allergen taxonomy - authoritative list (EU-14 standard)
ALLERGEN_CODES = {
    "GLUTEN", "CRUSTACEANS", "EGGS", "FISH", "PEANUTS",
    "SOYBEANS", "MILK", "NUTS", "CELERY", "MUSTARD",
    "SESAME", "SULPHITES", "LUPIN", "MOLLUSCS"
}

# Unit conversion factors (to base unit)
UNIT_CONVERSIONS = {
    # Weight conversions to kg
    "g": 0.001,
    "kg": 1.0,
    "mg": 0.000001,
    "lb": 0.453592,
    "oz": 0.0283495,
    
    # Volume conversions to L
    "ml": 0.001,
    "l": 1.0,
    "cl": 0.01,
    "dl": 0.1,
    "cup": 0.236588,
    "tbsp": 0.0147868,
    "tsp": 0.00492892,
    
    # Count/pieces (no conversion)
    "pcs": 1.0,
    "unit": 1.0,
    "piece": 1.0,
}

def normalize_quantity_to_base_unit(qty: float, from_unit: str, to_unit: str) -> float:
    """
    Normalize quantity from one unit to another using base unit conversion.
    
    Args:
        qty: Quantity in from_unit
        from_unit: Source unit (e.g., 'g', 'ml')
        to_unit: Target unit (e.g., 'kg', 'l')
    
    Returns:
        Normalized quantity in to_unit
        
    Example:
        normalize_quantity_to_base_unit(2, 'g', 'kg') -> 0.002
        normalize_quantity_to_base_unit(500, 'ml', 'l') -> 0.5
    """
    from_unit_lower = from_unit.lower()
    to_unit_lower = to_unit.lower()
    
    # Same unit, no conversion needed
    if from_unit_lower == to_unit_lower:
        return qty
    
    # Get conversion factors
    from_factor = UNIT_CONVERSIONS.get(from_unit_lower)
    to_factor = UNIT_CONVERSIONS.get(to_unit_lower)
    
    # If either unit is unknown, return original (no conversion)
    if from_factor is None or to_factor is None:
        return qty
    
    # Convert: from_unit -> base_unit -> to_unit
    # qty_in_base = qty * from_factor
    # qty_in_to_unit = qty_in_base / to_factor
    return qty * from_factor / to_factor

# Locale-specific allergen labels
ALLERGEN_LABELS = {
    "it-IT": {
        "GLUTEN": "glutine",
        "CRUSTACEANS": "crostacei",
        "MOLLUSCS": "molluschi",
        "EGGS": "uova",
        "FISH": "pesce",
        "TREE_NUTS": "frutta a guscio",
        "SOY": "soia",
        "DAIRY": "latticini",
        "SESAME": "sesamo",
        "CELERY": "sedano",
        "MUSTARD": "senape",
        "SULPHITES": "solfiti"
    },
    "en-US": {
        "GLUTEN": "gluten",
        "CRUSTACEANS": "crustaceans",
        "MOLLUSCS": "molluscs",
        "EGGS": "eggs",
        "FISH": "fish",
        "TREE_NUTS": "tree nuts",
        "SOY": "soy",
        "DAIRY": "dairy",
        "SESAME": "sesame",
        "CELERY": "celery",
        "MUSTARD": "mustard",
        "SULPHITES": "sulphites"
    }
}

# JWT Configuration
SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10080  # 7 days

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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
    isDisabled: Optional[bool] = False
    lastLoginAt: Optional[str] = None
    createdAt: str

class UserCreateByAdmin(BaseModel):
    email: EmailStr
    displayName: str
    roleKey: str  # admin, manager, waiter
    locale: Optional[str] = "en-US"
    sendInvite: bool = True  # True: send invite email, False: generate temp password

class UserUpdateByAdmin(BaseModel):
    displayName: Optional[str] = None
    roleKey: Optional[str] = None
    locale: Optional[str] = None
    isDisabled: Optional[bool] = None

class UserWithTempPassword(BaseModel):
    user: User
    tempPassword: Optional[str] = None  # Only present if sendInvite=False

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
    supplier: Optional[str] = None  # Deprecated, use preferredSupplierId
    preferredSupplierId: Optional[str] = None  # Supplier UUID reference
    allergen: Optional[str] = None  # Deprecated
    allergens: Optional[List[str]] = []  # List of allergen codes (GLUTEN, DAIRY, etc.)
    otherAllergens: Optional[List[str]] = []  # Free-text custom allergens
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
    supplier: Optional[str] = None  # Deprecated
    preferredSupplierId: Optional[str] = None  # Supplier UUID reference
    preferredSupplierName: Optional[str] = None  # Populated from lookup
    lastPrice: Optional[float] = None  # Last purchase price (packCost from most recent receiving)
    allergen: Optional[str] = None  # Deprecated
    allergens: List[str] = []  # List of allergen codes
    otherAllergens: List[str] = []  # Free-text custom allergens
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
    portions: Optional[int] = None  # Number of portions this preparation yields
    instructions: Optional[str] = None  # Preparation steps (procedure/method)
    notes: Optional[str] = None
    
    @field_validator('portions')
    @classmethod
    def validate_portions(cls, v):
        if v is not None and v < 1:
            raise ValueError('Portions must be at least 1')
        return v

class PreparationUpdate(BaseModel):
    """Update preparation request"""
    name: Optional[str] = None
    items: Optional[List[PreparationItem]] = None
    yield_: Optional[Yield] = None
    shelfLife: Optional[ShelfLife] = None
    portions: Optional[int] = None  # Number of portions this preparation yields
    instructions: Optional[str] = None  # Preparation steps (procedure/method)
    notes: Optional[str] = None
    
    @field_validator('portions')
    @classmethod
    def validate_portions(cls, v):
        if v is not None and v < 1:
            raise ValueError('Portions must be at least 1')
        return v

class Preparation(BaseModel):
    """Preparation model"""
    model_config = ConfigDict(extra="ignore")
    id: str
    restaurantId: str
    name: str
    items: List[PreparationItem]
    yield_: Optional[Yield] = None
    shelfLife: Optional[ShelfLife] = None
    portions: Optional[int] = None  # Number of portions this preparation yields
    instructions: Optional[str] = None  # Preparation steps (procedure/method)
    notes: Optional[str] = None
    cost: float  # Computed from ingredients with waste
    allergens: List[str]  # Computed allergen codes from ingredients
    otherAllergens: List[str] = []  # Computed custom allergens from ingredients
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
    qty: Optional[float] = None  # New schema
    qtyOnHand: Optional[float] = None  # Legacy schema
    unit: str
    countType: Optional[str] = None  # New schema
    unitCost: Optional[float] = None  # Legacy schema
    totalValue: Optional[float] = None  # Legacy schema
    batchExpiry: Optional[str] = None
    location: Optional[str] = None
    createdAt: Optional[str] = None  # New schema
    lastUpdated: Optional[str] = None  # Legacy schema

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
    instructions: Optional[str] = None  # Recipe preparation instructions

class RecipeUpdate(BaseModel):
    """Update recipe request"""
    name: Optional[str] = None
    category: Optional[str] = None
    portions: Optional[int] = None
    targetFoodCostPct: Optional[float] = None
    price: Optional[float] = None
    items: Optional[List[RecipeItem]] = None
    shelfLife: Optional[ShelfLife] = None
    instructions: Optional[str] = None  # Recipe preparation instructions

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
    allergens: List[str] = []  # Computed allergen codes from all items
    otherAllergens: List[str] = []  # Computed custom allergens from all items
    shelfLife: Optional[ShelfLife] = None
    instructions: Optional[str] = None  # Recipe preparation instructions
    createdAt: str
    updatedAt: Optional[str] = None

class SaleLine(BaseModel):
    recipeId: str
    qty: int  # Number of portions sold

class SalesCreate(BaseModel):
    date: str  # ISO format YYYY-MM-DD
    lines: List[SaleLine]
    revenue: Optional[int] = None  # Total revenue in minor units (cents)
    notes: Optional[str] = None

class Sales(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    restaurantId: str
    date: str
    lines: List[SaleLine]
    revenue: Optional[int] = None
    notes: Optional[str] = None
    stockDeductions: Optional[List[dict]] = None  # Audit trail of stock deductions
    createdAt: str
    updatedAt: Optional[str] = None

class WastageCreate(BaseModel):
    date: str  # ISO format YYYY-MM-DD
    type: str  # 'ingredient', 'preparation', or 'recipe' (full dish)
    itemId: str  # ID of ingredient, preparation, or recipe
    qty: float  # Quantity wasted
    unit: str  # Unit of measure
    reason: str  # Required: reason for wastage (spoilage, damage, error, etc.)
    notes: Optional[str] = None

class Wastage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    restaurantId: str
    date: str
    type: str  # 'ingredient', 'preparation', or 'recipe'
    itemId: str
    itemName: Optional[str] = None  # Denormalized for display
    qty: float
    unit: str
    reason: str
    notes: Optional[str] = None
    costImpact: Optional[int] = None  # Cost in minor units at time of wastage
    stockDeductions: Optional[List[dict]] = None  # Audit trail
    createdAt: str
    updatedAt: Optional[str] = None

# ============ PHASE 4: PREP LIST & ORDER LIST MODELS ============

class PrepListItem(BaseModel):
    """Prep list item for a specific date"""
    preparationId: str
    preparationName: Optional[str] = None  # Denormalized
    forecastQty: float  # Forecasted quantity needed
    availableQty: float  # Current stock available
    toMakeQty: float  # Quantity to prepare
    actualQty: Optional[float] = None  # Actual quantity made (for tracking)
    unit: str
    forecastSource: str  # 'sales_trend', 'manual_override', 'shelf_life'
    overrideQty: Optional[float] = None  # Manual override if set
    notes: Optional[str] = None

class PrepListCreate(BaseModel):
    """Create prep list for a date"""
    date: str  # ISO format YYYY-MM-DD
    items: List[PrepListItem]

class PrepList(BaseModel):
    """Prep list document"""
    model_config = ConfigDict(extra="ignore")
    id: str
    restaurantId: str
    date: str
    items: List[PrepListItem]
    createdAt: str
    updatedAt: Optional[str] = None

class OrderListItem(BaseModel):
    """Order list item for a specific date"""
    ingredientId: str
    ingredientName: Optional[str] = None  # Denormalized
    currentQty: float  # Current inventory level
    minStockQty: float  # Minimum stock threshold
    suggestedQty: float  # Suggested order quantity
    actualQty: Optional[float] = None  # Actual quantity ordered
    unit: str
    supplierId: Optional[str] = None
    supplierName: Optional[str] = None
    drivers: List[str]  # Reasons: 'low_stock', 'prep_needs', 'sales_forecast', 'expiring_soon'
    expiryDate: Optional[str] = None  # If item is expiring
    notes: Optional[str] = None

class OrderListCreate(BaseModel):
    """Create order list for a date"""
    date: str  # ISO format YYYY-MM-DD
    items: List[OrderListItem]

class OrderList(BaseModel):
    """Order list document"""
    model_config = ConfigDict(extra="ignore")
    id: str
    restaurantId: str
    date: str
    items: List[OrderListItem]
    createdAt: str
    updatedAt: Optional[str] = None

# ============ PHASE 5: P&L MODELS ============

class PLPeriod(BaseModel):
    """P&L period definition"""
    start: str  # YYYY-MM-DD
    end: str  # YYYY-MM-DD
    timezone: str = "Europe/Rome"
    granularity: str = "WEEK"  # Weekly Mon-Sun

class PLSection(BaseModel):
    """Generic P&L section with flexible line items"""
    total: float  # In major units, 2 decimals
    percent: Optional[float] = None  # Percent of turnover
    items: Optional[dict] = None  # Line items as key-value pairs

class PLSnapshot(BaseModel):
    """Complete P&L snapshot"""
    model_config = ConfigDict(extra="ignore")
    id: str
    restaurantId: str
    period: PLPeriod
    currency: str  # EUR or USD
    displayLocale: str  # it-IT or en-US
    
    # Sales section
    sales_turnover: float
    sales_food_beverage: float
    sales_delivery: float
    
    # COGS section
    cogs_food_beverage: float
    cogs_raw_waste: float
    cogs_total: float
    
    # OPEX section
    opex_non_food: float
    opex_platforms: float
    opex_total: float
    
    # Labour section
    labour_employees: float
    labour_staff_meal: float
    labour_total: float
    
    # Marketing section
    marketing_online_ads: float
    marketing_free_items: float
    marketing_total: float
    
    # Rent section
    rent_base_effective: float
    rent_garden: float
    rent_total: float
    
    # Other costs
    other_total: float
    
    # KPI
    kpi_ebitda: float
    
    # Metadata
    notes: Optional[str] = None
    createdAt: str
    updatedAt: Optional[str] = None

class PLSnapshotCreate(BaseModel):
    """Create P&L snapshot"""
    period: PLPeriod
    currency: str
    displayLocale: str
    sales_turnover: float
    sales_food_beverage: float
    sales_delivery: float
    cogs_food_beverage: float
    cogs_raw_waste: float
    opex_non_food: float
    opex_platforms: float
    labour_employees: float
    labour_staff_meal: float
    marketing_online_ads: float
    marketing_free_items: float
    rent_base_effective: float
    rent_garden: float
    other_total: float
    notes: Optional[str] = None

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
    fileType: Optional[str] = "general"  # price_list, contract, general
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
    importedFromOCR: Optional[bool] = False  # Flag for OCR imports
    ocrMetadata: Optional[Dict[str, Any]] = None  # OCR processing metadata
    invoiceNumber: Optional[str] = None  # Legacy field from old schema
    attachedFiles: Optional[List] = []  # Legacy field from old schema  
    createdBy: Optional[str] = None  # Legacy field from old schema
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
    Cost includes waste percentage and proper unit conversion.
    Uses 4-decimal precision internally for accuracy.
    Allergens normalized to EU-14 standard.
    """
    total_cost = 0
    all_allergens = set()
    all_other_allergens = set()
    
    for item in items:
        ingredient = await db.ingredients.find_one({"id": item["ingredientId"]}, {"_id": 0})
        if not ingredient:
            continue
        
        # Get effective cost per ingredient unit (includes waste)
        effective_cost_per_unit = ingredient.get("effectiveUnitCost", ingredient.get("unitCost", 0))
        ingredient_unit = ingredient.get("unit", "kg")
        item_qty = item["qty"]
        item_unit = item.get("unit", ingredient_unit)
        
        # Normalize item quantity to ingredient's unit for cost calculation
        normalized_qty = normalize_quantity_to_base_unit(item_qty, item_unit, ingredient_unit)
        
        # Calculate cost with 4-decimal precision
        item_cost = round(effective_cost_per_unit * normalized_qty, 4)
        total_cost += item_cost
        
        # Collect allergen codes
        allergens = ingredient.get("allergens", [])
        if allergens:
            all_allergens.update(allergens)
        
        # Collect other allergens
        other_allergens = ingredient.get("otherAllergens", [])
        if other_allergens:
            all_other_allergens.update(other_allergens)
        
        # Legacy support for single allergen field (migrate to codes)
        if ingredient.get("allergen"):
            legacy_allergen = ingredient["allergen"].upper().replace(" ", "_")
            if legacy_allergen in ALLERGEN_CODES:
                all_allergens.add(legacy_allergen)
            else:
                all_other_allergens.add(ingredient["allergen"])
    
    # Round total to 4 decimals (display will round to 2)
    return round(total_cost, 4), list(all_allergens), list(all_other_allergens)

async def compute_recipe_allergens(items: List[dict], db) -> tuple[List[str], List[str]]:
    """
    Compute recipe allergens from all items (ingredients + preparations).
    Returns (allergen_codes, other_allergens) - union of all allergens.
    """
    all_allergens = set()
    all_other_allergens = set()
    
    for item in items:
        if item["type"] == "ingredient":
            ingredient = await db.ingredients.find_one({"id": item["itemId"]}, {"_id": 0})
            if ingredient:
                # Collect allergen codes
                allergens = ingredient.get("allergens", [])
                if allergens:
                    all_allergens.update(allergens)
                
                # Collect other allergens
                other_allergens = ingredient.get("otherAllergens", [])
                if other_allergens:
                    all_other_allergens.update(other_allergens)
                
                # Legacy support
                if ingredient.get("allergen"):
                    legacy_allergen = ingredient["allergen"].upper().replace(" ", "_")
                    if legacy_allergen in ALLERGEN_CODES:
                        all_allergens.add(legacy_allergen)
                    else:
                        all_other_allergens.add(ingredient["allergen"])
        
        elif item["type"] == "preparation":
            preparation = await db.preparations.find_one({"id": item["itemId"]}, {"_id": 0})
            if preparation:
                # Collect allergen codes
                allergens = preparation.get("allergens", [])
                if allergens:
                    all_allergens.update(allergens)
                
                # Collect other allergens
                other_allergens = preparation.get("otherAllergens", [])
                if other_allergens:
                    all_other_allergens.update(other_allergens)
    
    return list(all_allergens), list(all_other_allergens)

async def deduct_stock_for_recipe(recipe_id: str, qty: int, restaurant_id: str, db) -> List[dict]:
    """
    Deduct stock for a recipe sale using WAC and prep-first priority.
    
    Priority:
    1. If recipe uses preparations → deduct prep stock first
    2. If prep stock insufficient or recipe uses raw ingredients → deduct raw ingredients
    
    Args:
        recipe_id: Recipe ID
        qty: Number of portions sold
        restaurant_id: Restaurant ID for tenant isolation
        db: Database connection
        
    Returns:
        List of stock deductions made (for audit trail)
    """
    deductions = []
    
    # Get recipe
    recipe = await db.recipes.find_one({"id": recipe_id, "restaurantId": restaurant_id}, {"_id": 0})
    if not recipe:
        raise HTTPException(status_code=404, detail=f"Recipe {recipe_id} not found")
    
    # Process each item in the recipe
    for item in recipe.get("items", []):
        item_qty_needed = item["qtyPerPortion"] * qty
        
        if item["type"] == "preparation":
            # Try to deduct preparation stock first
            prep_deduction = await deduct_preparation_stock(
                item["itemId"], item_qty_needed, restaurant_id, db
            )
            deductions.extend(prep_deduction)
            
        elif item["type"] == "ingredient":
            # Deduct raw ingredient stock
            ingredient_deduction = await deduct_ingredient_stock(
                item["itemId"], item_qty_needed, restaurant_id, db
            )
            deductions.append(ingredient_deduction)
    
    return deductions

async def deduct_preparation_stock(prep_id: str, qty: float, restaurant_id: str, db) -> List[dict]:
    """
    Deduct preparation stock. If insufficient, deduct underlying ingredients.
    
    Args:
        prep_id: Preparation ID
        qty: Quantity to deduct
        restaurant_id: Restaurant ID
        db: Database connection
        
    Returns:
        List of deductions made
    """
    deductions = []
    
    # Get preparation
    prep = await db.preparations.find_one({"id": prep_id, "restaurantId": restaurant_id}, {"_id": 0})
    if not prep:
        raise HTTPException(status_code=404, detail=f"Preparation {prep_id} not found")
    
    # Check if we have preparation stock in inventory
    prep_inventory = await db.inventory.find_one({
        "preparationId": prep_id,
        "restaurantId": restaurant_id
    })
    
    if prep_inventory and prep_inventory.get("qtyOnHand", 0) >= qty:
        # Deduct from preparation stock
        new_qty = prep_inventory["qtyOnHand"] - qty
        await db.inventory.update_one(
            {"preparationId": prep_id, "restaurantId": restaurant_id},
            {"$set": {"qtyOnHand": new_qty, "updatedAt": datetime.now(timezone.utc).isoformat()}}
        )
        
        deductions.append({
            "type": "preparation",
            "itemId": prep_id,
            "itemName": prep["name"],
            "qtyDeducted": qty,
            "unit": prep.get("unit", "portions"),
            "remainingQty": new_qty
        })
    else:
        # Insufficient prep stock → deduct underlying ingredients
        # Calculate how much prep stock we can use (if any)
        prep_qty_available = prep_inventory.get("qtyOnHand", 0) if prep_inventory else 0
        prep_qty_from_stock = min(prep_qty_available, qty)
        prep_qty_from_ingredients = qty - prep_qty_from_stock
        
        if prep_qty_from_stock > 0:
            # Use available prep stock
            await db.inventory.update_one(
                {"preparationId": prep_id, "restaurantId": restaurant_id},
                {"$set": {"qtyOnHand": 0, "updatedAt": datetime.now(timezone.utc).isoformat()}}
            )
            deductions.append({
                "type": "preparation",
                "itemId": prep_id,
                "itemName": prep["name"],
                "qtyDeducted": prep_qty_from_stock,
                "unit": prep.get("unit", "portions"),
                "remainingQty": 0
            })
        
        if prep_qty_from_ingredients > 0:
            # Deduct underlying ingredients for the shortfall
            # Scale ingredient quantities by the prep yield
            prep_yield_obj = prep.get("yield") or {}
            prep_yield = prep_yield_obj.get("value", 1)
            scale_factor = (prep_qty_from_ingredients / prep_yield) if prep_yield > 0 else prep_qty_from_ingredients
            
            for prep_item in prep.get("items", []):
                ingredient_qty_needed = prep_item["qty"] * scale_factor
                ingredient_deduction = await deduct_ingredient_stock(
                    prep_item["ingredientId"], ingredient_qty_needed, restaurant_id, db
                )
                deductions.append(ingredient_deduction)
    
    return deductions

async def deduct_ingredient_stock(ingredient_id: str, qty: float, restaurant_id: str, db) -> dict:
    """
    Deduct ingredient stock using WAC (Weighted Average Cost).
    
    Args:
        ingredient_id: Ingredient ID
        qty: Quantity to deduct
        restaurant_id: Restaurant ID
        db: Database connection
        
    Returns:
        Deduction record
    """
    # Get ingredient
    ingredient = await db.ingredients.find_one({"id": ingredient_id, "restaurantId": restaurant_id}, {"_id": 0})
    if not ingredient:
        raise HTTPException(status_code=404, detail=f"Ingredient {ingredient_id} not found")
    
    # Get inventory record
    inventory = await db.inventory.find_one({
        "ingredientId": ingredient_id,
        "restaurantId": restaurant_id
    })
    
    if not inventory:
        # No inventory record → log as shortage
        return {
            "type": "ingredient",
            "itemId": ingredient_id,
            "itemName": ingredient["name"],
            "qtyDeducted": qty,
            "unit": ingredient["unit"],
            "remainingQty": 0,
            "shortage": qty
        }
    
    current_qty = inventory.get("qtyOnHand", 0)
    
    if current_qty < qty:
        # Partial deduction → shortage
        await db.inventory.update_one(
            {"ingredientId": ingredient_id, "restaurantId": restaurant_id},
            {"$set": {"qtyOnHand": 0, "updatedAt": datetime.now(timezone.utc).isoformat()}}
        )
        
        return {
            "type": "ingredient",
            "itemId": ingredient_id,
            "itemName": ingredient["name"],
            "qtyDeducted": current_qty,
            "unit": ingredient["unit"],
            "remainingQty": 0,
            "shortage": qty - current_qty
        }
    else:
        # Full deduction
        new_qty = current_qty - qty
        await db.inventory.update_one(
            {"ingredientId": ingredient_id, "restaurantId": restaurant_id},
            {"$set": {"qtyOnHand": new_qty, "updatedAt": datetime.now(timezone.utc).isoformat()}}
        )
        
        return {
            "type": "ingredient",
            "itemId": ingredient_id,
            "itemName": ingredient["name"],
            "qtyDeducted": qty,
            "unit": ingredient["unit"],
            "remainingQty": new_qty
        }

# ============ PHASE 4: FORECAST ALGORITHMS ============

async def forecast_prep_needs(date: str, restaurant_id: str, db) -> List[dict]:
    """
    Forecast preparation needs for a specific date based on:
    1. Weekly sales trend (same weekday, last 4 weeks average)
    2. Current prep stock levels
    3. Shelf life considerations
    
    Args:
        date: Target date (ISO format YYYY-MM-DD)
        restaurant_id: Restaurant ID
        db: Database connection
        
    Returns:
        List of prep items with forecast quantities
    """
    from datetime import datetime, timedelta
    
    target_date = datetime.fromisoformat(date)
    weekday = target_date.weekday()  # 0=Monday, 6=Sunday
    
    # Get all preparations
    preparations = await db.preparations.find({"restaurantId": restaurant_id}, {"_id": 0}).to_list(1000)
    
    prep_forecast = []
    
    for prep in preparations:
        # Find recipes that use this preparation
        recipes_using_prep = await db.recipes.find({
            "restaurantId": restaurant_id,
            "items.type": "preparation",
            "items.itemId": prep["id"]
        }, {"_id": 0}).to_list(1000)
        
        if not recipes_using_prep:
            continue
        
        # Get sales for same weekday over last 4 weeks
        weekly_sales = []
        for week_offset in range(1, 5):
            past_date = target_date - timedelta(weeks=week_offset)
            sales_on_date = await db.sales.find({
                "restaurantId": restaurant_id,
                "date": past_date.strftime("%Y-%m-%d")
            }, {"_id": 0}).to_list(1000)
            
            prep_qty_needed = 0
            for sale in sales_on_date:
                for line in sale.get("lines", []):
                    # Find if this recipe uses our prep
                    recipe = next((r for r in recipes_using_prep if r["id"] == line["recipeId"]), None)
                    if recipe:
                        # Find prep item in recipe
                        prep_item = next((item for item in recipe["items"] if item.get("itemId") == prep["id"]), None)
                        if prep_item:
                            prep_qty_needed += prep_item["qtyPerPortion"] * line["qty"]
            
            weekly_sales.append(prep_qty_needed)
        
        # Calculate average (forecast)
        avg_forecast = sum(weekly_sales) / len(weekly_sales) if weekly_sales else 0
        
        # Check current prep stock
        prep_inventory = await db.inventory.find_one({
            "preparationId": prep["id"],
            "restaurantId": restaurant_id
        })
        
        available_qty = prep_inventory.get("qtyOnHand", 0) if prep_inventory else 0
        
        # Calculate to-make quantity
        to_make_qty = max(0, avg_forecast - available_qty)
        
        prep_forecast.append({
            "preparationId": prep["id"],
            "preparationName": prep["name"],
            "forecastQty": round(avg_forecast, 2),
            "availableQty": round(available_qty, 2),
            "toMakeQty": round(to_make_qty, 2),
            "unit": prep.get("unit", "portions"),
            "forecastSource": "sales_trend"
        })
    
    return prep_forecast

async def forecast_order_needs(date: str, restaurant_id: str, db) -> List[dict]:
    """
    Forecast ingredient order needs based on:
    1. Current inventory levels vs min stock
    2. Upcoming prep list requirements
    3. Sales forecast for same weekday
    4. Expiry alerts (shelf life < 3 days)
    
    Args:
        date: Target date (ISO format YYYY-MM-DD)
        restaurant_id: Restaurant ID
        db: Database connection
        
    Returns:
        List of order items with suggestions and drivers
    """
    from datetime import datetime, timedelta
    
    target_date = datetime.fromisoformat(date)
    
    # Get all ingredients
    ingredients = await db.ingredients.find({"restaurantId": restaurant_id}, {"_id": 0}).to_list(1000)
    
    order_suggestions = []
    
    for ing in ingredients:
        # Get current inventory
        inventory = await db.inventory.find_one({
            "ingredientId": ing["id"],
            "restaurantId": restaurant_id
        })
        
        current_qty = inventory.get("qtyOnHand", 0) if inventory else 0
        min_stock = ing.get("minStockQty", 0)
        
        drivers = []
        suggested_qty = 0
        expiry_date = None
        
        # Driver 1: Low stock
        if current_qty < min_stock:
            drivers.append("low_stock")
            suggested_qty += (min_stock - current_qty)
        
        # Driver 2: Expiring soon (if shelf life < 3 days from batch)
        if inventory and inventory.get("batchExpiry"):
            try:
                expiry = datetime.fromisoformat(inventory["batchExpiry"])
                days_until_expiry = (expiry - target_date).days
                if 0 < days_until_expiry <= 3:
                    drivers.append("expiring_soon")
                    expiry_date = inventory["batchExpiry"]
            except:
                pass
        
        # Driver 3: Prep needs (check if used in upcoming prep list)
        # Simplified: check if ingredient is in any preparation
        preps_using_ing = await db.preparations.find({
            "restaurantId": restaurant_id,
            "items.ingredientId": ing["id"]
        }, {"_id": 0}).to_list(1000)
        
        if preps_using_ing:
            drivers.append("prep_needs")
            # Estimate additional need (simplified)
            suggested_qty += min_stock * 0.5
        
        # Only add to order list if there are drivers
        if drivers:
            # Get preferred supplier (simplified - first supplier)
            supplier = await db.suppliers.find_one({"restaurantId": restaurant_id}, {"_id": 0})
            
            order_suggestions.append({
                "ingredientId": ing["id"],
                "ingredientName": ing["name"],
                "currentQty": round(current_qty, 2),
                "minStockQty": round(min_stock, 2),
                "suggestedQty": round(suggested_qty, 2),
                "unit": ing["unit"],
                "supplierId": supplier["id"] if supplier else None,
                "supplierName": supplier["name"] if supplier else None,
                "drivers": drivers,
                "expiryDate": expiry_date
            })
    
    return order_suggestions

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
    """
    Comprehensive health check endpoint
    Verifies:
    - Database connection
    - JWT secrets present
    - Essential services
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": "disconnected",
        "jwt_secrets": "missing",
        "currency": DEFAULT_CURRENCY,
        "locale": DEFAULT_LOCALE
    }
    
    # Check database
    try:
        await db.command("ping")
        health_status["database"] = "connected"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["database"] = f"error: {str(e)}"
    
    # Check JWT secrets
    if SECRET_KEY and len(SECRET_KEY) > 10:
        health_status["jwt_secrets"] = "present"
    else:
        health_status["status"] = "unhealthy"
        health_status["jwt_secrets"] = "missing or too short"
    
    # Check critical dependencies
    try:
        import magic
        health_status["libmagic"] = "available"
    except ImportError:
        health_status["libmagic"] = "missing"
        health_status["status"] = "degraded"
    
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        health_status["tesseract"] = "available"
    except:
        health_status["tesseract"] = "unavailable"
    
    return health_status


@api_router.get("/health/ocr")
async def health_check_ocr():
    """
    OCR-specific health check endpoint
    Returns OCR service availability and supported languages
    """
    import subprocess
    
    ocr_health = {
        "ok": False,
        "service": "tesseract",
        "version": None,
        "langs": [],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "error": None
    }
    
    try:
        # Check tesseract version
        version_result = subprocess.run(
            ['tesseract', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if version_result.returncode == 0:
            version_line = version_result.stdout.split('\n')[0]
            ocr_health["version"] = version_line.strip()
        
        # Check available languages
        langs_result = subprocess.run(
            ['tesseract', '--list-langs'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if langs_result.returncode == 0:
            lines = langs_result.stdout.strip().split('\n')
            # Skip the first line (header)
            ocr_health["langs"] = [lang.strip() for lang in lines[1:] if lang.strip()]
            ocr_health["ok"] = True
        else:
            ocr_health["error"] = "Failed to list languages"
    
    except FileNotFoundError:
        ocr_health["error"] = "Tesseract binary not found in PATH"
    except subprocess.TimeoutExpired:
        ocr_health["error"] = "Tesseract command timed out"
    except Exception as e:
        ocr_health["error"] = str(e)
    
    return ocr_health

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

# ============ USER MANAGEMENT ROUTES (ADMIN ONLY) ============

@api_router.get("/users", response_model=List[User])
async def get_users(current_user: dict = Depends(get_current_user)):
    """Get all users in the admin's restaurant"""
    await check_subscription(current_user)
    
    # Only admins can manage users
    if current_user.get("roleKey") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get all users in the same restaurant
    users = await db.users.find(
        {"restaurantId": current_user["restaurantId"]},
        {"_id": 0, "password": 0}  # Exclude password field
    ).to_list(1000)
    
    return [User(**user) for user in users]

@api_router.post("/users", response_model=UserWithTempPassword)
async def create_user(user_data: UserCreateByAdmin, current_user: dict = Depends(get_current_user)):
    """Create a new user in the admin's restaurant"""
    await check_subscription(current_user)
    
    # Only admins can create users
    if current_user.get("roleKey") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check if user already exists
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    # Validate roleKey
    valid_roles = ["admin", "manager", "waiter"]
    if user_data.roleKey not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}")
    
    user_id = str(uuid.uuid4())
    temp_password = None
    
    if user_data.sendInvite:
        # Generate invite token and send email
        invite_token = secrets.token_urlsafe(32)
        # TODO: Send invite email (stub for now)
        # In production, send email with link: /reset-password?token={invite_token}
        hashed_password = pwd_context.hash(secrets.token_urlsafe(16))  # Random password until they set it
    else:
        # Generate temporary password
        temp_password = secrets.token_urlsafe(12)
        hashed_password = pwd_context.hash(temp_password)
    
    user = {
        "id": user_id,
        "email": user_data.email,
        "displayName": user_data.displayName,
        "password": hashed_password,
        "restaurantId": current_user["restaurantId"],
        "role": user_data.roleKey,  # For backward compatibility
        "roleKey": user_data.roleKey,
        "locale": user_data.locale or "en-US",
        "isDisabled": False,
        "lastLoginAt": None,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user)
    
    # Log audit
    await log_audit(
        db,
        current_user["restaurantId"],
        "user",
        "create",
        current_user["id"],
        {"userId": user_id, "email": user_data.email, "roleKey": user_data.roleKey}
    )
    
    user.pop("_id", None)
    user.pop("password", None)
    
    return UserWithTempPassword(user=User(**user), tempPassword=temp_password)

@api_router.put("/users/{user_id}", response_model=User)
async def update_user(user_id: str, user_data: UserUpdateByAdmin, current_user: dict = Depends(get_current_user)):
    """Update a user (admin only)"""
    await check_subscription(current_user)
    
    # Only admins can update users
    if current_user.get("roleKey") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check if user exists and is in the same restaurant
    existing = await db.users.find_one({
        "id": user_id,
        "restaurantId": current_user["restaurantId"]
    })
    
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Cannot disable or modify self
    if user_id == current_user["id"]:
        if user_data.isDisabled:
            raise HTTPException(status_code=400, detail="Cannot disable your own account")
        if user_data.roleKey and user_data.roleKey != current_user.get("roleKey"):
            raise HTTPException(status_code=400, detail="Cannot change your own role")
    
    # Build update data
    update_data = {}
    if user_data.displayName is not None:
        update_data["displayName"] = user_data.displayName
    if user_data.roleKey is not None:
        # Validate roleKey
        valid_roles = ["admin", "manager", "waiter"]
        if user_data.roleKey not in valid_roles:
            raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}")
        update_data["roleKey"] = user_data.roleKey
        update_data["role"] = user_data.roleKey  # Backward compatibility
    if user_data.locale is not None:
        update_data["locale"] = user_data.locale
    if user_data.isDisabled is not None:
        update_data["isDisabled"] = user_data.isDisabled
    
    if update_data:
        await db.users.update_one(
            {"id": user_id},
            {"$set": update_data}
        )
    
    # Log audit
    await log_audit(
        db,
        current_user["restaurantId"],
        "user",
        "update",
        current_user["id"],
        {"userId": user_id, "changes": update_data}
    )
    
    # Get updated user
    updated_user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    return User(**updated_user)

@api_router.post("/users/{user_id}/reset-password")
async def admin_reset_password(user_id: str, current_user: dict = Depends(get_current_user)):
    """Admin-initiated password reset"""
    await check_subscription(current_user)
    
    # Only admins can reset passwords
    if current_user.get("roleKey") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check if user exists and is in the same restaurant
    user = await db.users.find_one({
        "id": user_id,
        "restaurantId": current_user["restaurantId"]
    })
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Generate reset token
    reset_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    
    await db.password_resets.insert_one({
        "token": reset_token,
        "userId": user_id,
        "expiresAt": expires_at.isoformat(),
        "used": False,
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    # TODO: Send password reset email
    # In production: send email with link: /reset-password?token={reset_token}
    
    # Log audit
    await log_audit(
        db,
        current_user["restaurantId"],
        "user",
        "reset_password",
        current_user["id"],
        {"userId": user_id, "email": user["email"]}
    )
    
    return {"message": "Password reset email sent", "token": reset_token}  # Remove token in production

@api_router.delete("/users/{user_id}")
async def delete_user(user_id: str, current_user: dict = Depends(get_current_user)):
    """Delete/disable a user (soft delete preferred)"""
    await check_subscription(current_user)
    
    # Only admins can delete users
    if current_user.get("roleKey") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Cannot delete self
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    # Check if user exists and is in the same restaurant
    user = await db.users.find_one({
        "id": user_id,
        "restaurantId": current_user["restaurantId"]
    })
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Soft delete: disable user instead of deleting
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"isDisabled": True}}
    )
    
    # Log audit
    await log_audit(
        db,
        current_user["restaurantId"],
        "user",
        "delete",
        current_user["id"],
        {"userId": user_id, "email": user["email"]}
    )
    
    return {"message": "User disabled successfully"}

# ============ INGREDIENTS ROUTES ============

@api_router.post("/ingredients", response_model=Ingredient)
async def create_ingredient(ingredient_data: IngredientCreate, current_user: dict = Depends(get_current_user)):
    await check_subscription(current_user)
    
    ingredient_id = str(uuid.uuid4())
    unit_cost = ingredient_data.packCost / ingredient_data.packSize
    waste_pct = ingredient_data.wastePct or 0
    effective_unit_cost = unit_cost * (1 + waste_pct / 100)
    
    # Normalize allergen codes to uppercase for consistency
    allergens = [a.upper() for a in (ingredient_data.allergens or [])]
    
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
        "preferredSupplierId": ingredient_data.preferredSupplierId,
        "allergen": ingredient_data.allergen,
        "allergens": allergens,
        "otherAllergens": ingredient_data.otherAllergens or [],
        "minStockQty": ingredient_data.minStockQty,
        "category": ingredient_data.category or "food",
        "wastePct": waste_pct,
        "shelfLife": ingredient_data.shelfLife.dict() if ingredient_data.shelfLife else None,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.ingredients.insert_one(ingredient)
    
    # Populate supplier name
    if ingredient.get("preferredSupplierId"):
        supplier = await db.suppliers.find_one({"id": ingredient["preferredSupplierId"]}, {"_id": 0})
        if supplier:
            ingredient["preferredSupplierName"] = supplier.get("name")
    
    return Ingredient(**ingredient)

@api_router.get("/ingredients", response_model=List[Ingredient])
async def get_ingredients(current_user: dict = Depends(get_current_user)):
    await check_subscription(current_user)
    ingredients = await db.ingredients.find({"restaurantId": current_user["restaurantId"]}, {"_id": 0}).to_list(1000)
    
    # Populate supplier name if preferredSupplierId exists
    for ing in ingredients:
        if ing.get("preferredSupplierId"):
            supplier = await db.suppliers.find_one({"id": ing["preferredSupplierId"]}, {"_id": 0})
            if supplier:
                ing["preferredSupplierName"] = supplier.get("name")
    
    return [Ingredient(**ing) for ing in ingredients]

@api_router.get("/ingredients/{ingredient_id}", response_model=Ingredient)
async def get_ingredient(ingredient_id: str, current_user: dict = Depends(get_current_user)):
    """Get a single ingredient by ID"""
    await check_subscription(current_user)
    
    ingredient = await db.ingredients.find_one({
        "id": ingredient_id,
        "restaurantId": current_user["restaurantId"]
    }, {"_id": 0})
    
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    
    # Populate supplier name if preferredSupplierId exists
    if ingredient.get("preferredSupplierId"):
        supplier = await db.suppliers.find_one({"id": ingredient["preferredSupplierId"]}, {"_id": 0})
        if supplier:
            ingredient["preferredSupplierName"] = supplier.get("name")
    
    return Ingredient(**ingredient)

@api_router.put("/ingredients/{ingredient_id}", response_model=Ingredient)
async def update_ingredient(ingredient_id: str, ingredient_data: IngredientCreate, current_user: dict = Depends(get_current_user)):
    await check_subscription(current_user)
    
    # RBAC: Only admin and manager can update ingredients
    if current_user["roleKey"] not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Only administrators and managers can update ingredients")
    
    existing = await db.ingredients.find_one({"id": ingredient_id, "restaurantId": current_user["restaurantId"]})
    if not existing:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    
    unit_cost = ingredient_data.packCost / ingredient_data.packSize
    waste_pct = ingredient_data.wastePct or 0
    effective_unit_cost = unit_cost * (1 + waste_pct / 100)
    
    # Normalize allergen codes to uppercase for consistency
    allergens = [a.upper() for a in (ingredient_data.allergens or [])]
    
    update_data = {
        "name": ingredient_data.name,
        "unit": ingredient_data.unit,
        "packSize": ingredient_data.packSize,
        "packCost": ingredient_data.packCost,
        "unitCost": unit_cost,
        "effectiveUnitCost": effective_unit_cost,
        "supplier": ingredient_data.supplier,
        "preferredSupplierId": ingredient_data.preferredSupplierId,
        "allergen": ingredient_data.allergen,
        "allergens": allergens,
        "otherAllergens": ingredient_data.otherAllergens or [],
        "minStockQty": ingredient_data.minStockQty,
        "wastePct": waste_pct,
        "shelfLife": ingredient_data.shelfLife.dict() if ingredient_data.shelfLife else None
    }
    
    await db.ingredients.update_one({"id": ingredient_id}, {"$set": update_data})
    updated = await db.ingredients.find_one({"id": ingredient_id}, {"_id": 0})
    
    # Populate supplier name
    if updated.get("preferredSupplierId"):
        supplier = await db.suppliers.find_one({"id": updated["preferredSupplierId"]}, {"_id": 0})
        if supplier:
            updated["preferredSupplierName"] = supplier.get("name")
    
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
    cost, allergens, other_allergens = await compute_preparation_cost_and_allergens(items_dict, db)
    
    preparation = {
        "id": str(uuid.uuid4()),
        "restaurantId": current_user["restaurantId"],
        "name": prep.name,
        "items": items_dict,
        "yield": prep.yield_.dict() if prep.yield_ else None,
        "shelfLife": prep.shelfLife.dict() if prep.shelfLife else None,
        "portions": prep.portions,  # Number of portions
        "instructions": prep.instructions,  # Preparation procedure/method
        "notes": prep.notes,
        "cost": cost,
        "allergens": allergens,
        "otherAllergens": other_allergens,
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
        cost, allergens, other_allergens = await compute_preparation_cost_and_allergens(items_dict, db)
        update_data["cost"] = cost
        update_data["allergens"] = allergens
        update_data["otherAllergens"] = other_allergens
    
    if prep_update.yield_ is not None:
        update_data["yield"] = prep_update.yield_.dict()
    
    if prep_update.shelfLife is not None:
        update_data["shelfLife"] = prep_update.shelfLife.dict()
    
    if prep_update.portions is not None:
        update_data["portions"] = prep_update.portions
    
    if prep_update.instructions is not None:
        update_data["instructions"] = prep_update.instructions
    
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
    try:
        await check_subscription(current_user)
        inventory = await db.inventory.find({"restaurantId": current_user["restaurantId"]}, {"_id": 0}).to_list(1000)
        
        result = []
        for inv in inventory:
            try:
                result.append(Inventory(**inv))
            except Exception as e:
                logger.error(f"Error serializing inventory record {inv.get('id', 'unknown')}: {e}")
                logger.error(f"Record data keys: {list(inv.keys())}")
                # Continue with other records
        
        return result
    except Exception as e:
        logger.error(f"Error in get_inventory: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

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
    allergens, other_allergens = await compute_recipe_allergens(items_dict, db)
    
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
        "otherAllergens": other_allergens,
        "shelfLife": recipe_data.shelfLife.dict() if recipe_data.shelfLife else None,
        "instructions": recipe_data.instructions,
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
        # Validate non-empty items array
        if len(recipe_data.items) == 0:
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
        
        items_dict = [item.dict() for item in recipe_data.items]
        update_data["items"] = items_dict
        # Recompute allergens when items change
        allergens, other_allergens = await compute_recipe_allergens(items_dict, db)
        update_data["allergens"] = allergens
        update_data["otherAllergens"] = other_allergens
    
    if recipe_data.shelfLife is not None:
        update_data["shelfLife"] = recipe_data.shelfLife.dict()
    
    if recipe_data.instructions is not None:
        update_data["instructions"] = recipe_data.instructions
    
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
    
    # Validate non-empty lines array
    if not sales_data.lines or len(sales_data.lines) == 0:
        raise HTTPException(status_code=422, detail="Sales must have at least one line item")
    
    # Validate all recipes exist
    all_deductions = []
    for line in sales_data.lines:
        recipe = await db.recipes.find_one(
            {"id": line.recipeId, "restaurantId": current_user["restaurantId"]}
        )
        if not recipe:
            raise HTTPException(status_code=404, detail=f"Recipe {line.recipeId} not found")
        
        # Deduct stock for this recipe sale
        deductions = await deduct_stock_for_recipe(
            line.recipeId, line.qty, current_user["restaurantId"], db
        )
        all_deductions.extend(deductions)
    
    sales_id = str(uuid.uuid4())
    sales = {
        "id": sales_id,
        "restaurantId": current_user["restaurantId"],
        "date": sales_data.date,
        "lines": [line.model_dump() for line in sales_data.lines],
        "revenue": sales_data.revenue,
        "notes": sales_data.notes,
        "stockDeductions": all_deductions,  # Audit trail
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "updatedAt": None
    }
    
    await db.sales.insert_one(sales)
    
    # Log audit
    await log_audit(
        db,
        current_user["restaurantId"],
        "sales",
        "create",
        current_user["id"],
        {"salesId": sales_id, "date": sales_data.date, "linesCount": len(sales_data.lines)}
    )
    
    sales.pop("_id", None)
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
    
    # Get item details and deduct stock
    deductions = []
    item_name = ""
    cost_impact = 0
    
    if wastage_data.type == "ingredient":
        # Deduct ingredient stock
        deduction = await deduct_ingredient_stock(
            wastage_data.itemId, wastage_data.qty, current_user["restaurantId"], db
        )
        deductions.append(deduction)
        item_name = deduction["itemName"]
        
        # Calculate cost impact
        ingredient = await db.ingredients.find_one(
            {"id": wastage_data.itemId, "restaurantId": current_user["restaurantId"]},
            {"_id": 0}
        )
        if ingredient:
            effective_cost = ingredient.get("effectiveUnitCost", ingredient.get("unitCost", 0))
            cost_impact = int(effective_cost * wastage_data.qty)
    
    elif wastage_data.type == "preparation":
        # Deduct preparation stock
        prep_deductions = await deduct_preparation_stock(
            wastage_data.itemId, wastage_data.qty, current_user["restaurantId"], db
        )
        deductions.extend(prep_deductions)
        
        # Get prep details for name and cost
        prep = await db.preparations.find_one(
            {"id": wastage_data.itemId, "restaurantId": current_user["restaurantId"]},
            {"_id": 0}
        )
        if prep:
            item_name = prep["name"]
            cost_impact = int(prep.get("cost", 0) * wastage_data.qty)
    
    elif wastage_data.type == "recipe":
        # Deduct recipe items (full dish waste)
        recipe_deductions = await deduct_stock_for_recipe(
            wastage_data.itemId, int(wastage_data.qty), current_user["restaurantId"], db
        )
        deductions.extend(recipe_deductions)
        
        # Get recipe details
        recipe = await db.recipes.find_one(
            {"id": wastage_data.itemId, "restaurantId": current_user["restaurantId"]},
            {"_id": 0}
        )
        if recipe:
            item_name = recipe["name"]
            # Cost impact = sum of all ingredient/prep costs
            # (simplified: we'll use the recipe cost if available)
            cost_impact = 0  # TODO: Calculate from recipe items
    
    wastage_id = str(uuid.uuid4())
    wastage = {
        "id": wastage_id,
        "restaurantId": current_user["restaurantId"],
        "date": wastage_data.date,
        "type": wastage_data.type,
        "itemId": wastage_data.itemId,
        "itemName": item_name,
        "qty": wastage_data.qty,
        "unit": wastage_data.unit,
        "reason": wastage_data.reason,
        "notes": wastage_data.notes,
        "costImpact": cost_impact,
        "stockDeductions": deductions,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "updatedAt": None
    }
    
    await db.wastage.insert_one(wastage)
    
    # Log audit
    await log_audit(
        db,
        current_user["restaurantId"],
        "wastage",
        "create",
        current_user["id"],
        {"wastageId": wastage_id, "type": wastage_data.type, "itemId": wastage_data.itemId, "qty": wastage_data.qty}
    )
    
    wastage.pop("_id", None)
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

# ============ PHASE 4: PREP LIST ROUTES ============

@api_router.get("/prep-list/forecast")
async def get_prep_forecast(date: str, current_user: dict = Depends(get_current_user)):
    """Get forecasted prep needs for a date"""
    await check_subscription(current_user)
    
    forecast = await forecast_prep_needs(date, current_user["restaurantId"], db)
    return {"date": date, "items": forecast}

@api_router.get("/prep-list", response_model=List[PrepList])
async def get_prep_lists(current_user: dict = Depends(get_current_user)):
    """Get all prep lists"""
    await check_subscription(current_user)
    
    prep_lists = await db.prep_lists.find(
        {"restaurantId": current_user["restaurantId"]},
        {"_id": 0}
    ).to_list(1000)
    
    return [PrepList(**pl) for pl in prep_lists]

@api_router.post("/prep-list", response_model=PrepList)
async def create_prep_list(prep_data: PrepListCreate, current_user: dict = Depends(get_current_user)):
    """Create or update prep list for a date"""
    await check_subscription(current_user)
    
    # Check if prep list already exists for this date
    existing = await db.prep_lists.find_one({
        "restaurantId": current_user["restaurantId"],
        "date": prep_data.date
    })
    
    if existing:
        # Update existing
        await db.prep_lists.update_one(
            {"id": existing["id"]},
            {"$set": {
                "items": [item.model_dump() for item in prep_data.items],
                "updatedAt": datetime.now(timezone.utc).isoformat()
            }}
        )
        prep_list_id = existing["id"]
    else:
        # Create new
        prep_list_id = str(uuid.uuid4())
        prep_list = {
            "id": prep_list_id,
            "restaurantId": current_user["restaurantId"],
            "date": prep_data.date,
            "items": [item.model_dump() for item in prep_data.items],
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "updatedAt": None
        }
        await db.prep_lists.insert_one(prep_list)
    
    # Log audit
    await log_audit(
        db,
        current_user["restaurantId"],
        "prep_list",
        "create" if not existing else "update",
        current_user["id"],
        {"date": prep_data.date, "itemsCount": len(prep_data.items)}
    )
    
    # Get and return
    result = await db.prep_lists.find_one({"id": prep_list_id}, {"_id": 0})
    return PrepList(**result)

# ============ PHASE 4: ORDER LIST ROUTES ============

@api_router.get("/order-list/forecast")
async def get_order_forecast(date: str, current_user: dict = Depends(get_current_user)):
    """Get forecasted order needs for a date"""
    await check_subscription(current_user)
    
    forecast = await forecast_order_needs(date, current_user["restaurantId"], db)
    return {"date": date, "items": forecast}

@api_router.get("/order-list", response_model=List[OrderList])
async def get_order_lists(current_user: dict = Depends(get_current_user)):
    """Get all order lists"""
    await check_subscription(current_user)
    
    order_lists = await db.order_lists.find(
        {"restaurantId": current_user["restaurantId"]},
        {"_id": 0}
    ).to_list(1000)
    
    return [OrderList(**ol) for ol in order_lists]

@api_router.post("/order-list", response_model=OrderList)
async def create_order_list(order_data: OrderListCreate, current_user: dict = Depends(get_current_user)):
    """Create or update order list for a date"""
    await check_subscription(current_user)
    
    # Check if order list already exists for this date
    existing = await db.order_lists.find_one({
        "restaurantId": current_user["restaurantId"],
        "date": order_data.date
    })
    
    if existing:
        # Update existing
        await db.order_lists.update_one(
            {"id": existing["id"]},
            {"$set": {
                "items": [item.model_dump() for item in order_data.items],
                "updatedAt": datetime.now(timezone.utc).isoformat()
            }}
        )
        order_list_id = existing["id"]
    else:
        # Create new
        order_list_id = str(uuid.uuid4())
        order_list = {
            "id": order_list_id,
            "restaurantId": current_user["restaurantId"],
            "date": order_data.date,
            "items": [item.model_dump() for item in order_data.items],
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "updatedAt": None
        }
        await db.order_lists.insert_one(order_list)
    
    # Log audit
    await log_audit(
        db,
        current_user["restaurantId"],
        "order_list",
        "create" if not existing else "update",
        current_user["id"],
        {"date": order_data.date, "itemsCount": len(order_data.items)}
    )
    
    # Get and return
    result = await db.order_lists.find_one({"id": order_list_id}, {"_id": 0})
    return OrderList(**result)

# ============ PHASE 5: P&L ROUTES ============

@api_router.post("/pl/snapshot", response_model=PLSnapshot)
async def create_pl_snapshot(pl_data: PLSnapshotCreate, current_user: dict = Depends(get_current_user)):
    """Create P&L snapshot for a period"""
    await check_subscription(current_user)
    
    # Calculate totals
    cogs_total = pl_data.cogs_food_beverage + pl_data.cogs_raw_waste
    opex_total = pl_data.opex_non_food + pl_data.opex_platforms
    labour_total = pl_data.labour_employees + pl_data.labour_staff_meal
    marketing_total = pl_data.marketing_online_ads + pl_data.marketing_free_items
    rent_total = pl_data.rent_base_effective + pl_data.rent_garden
    
    # Calculate EBITDA
    ebitda = (pl_data.sales_turnover - cogs_total - opex_total - 
              labour_total - marketing_total - rent_total - pl_data.other_total)
    
    pl_id = str(uuid.uuid4())
    snapshot = {
        "id": pl_id,
        "restaurantId": current_user["restaurantId"],
        "period": pl_data.period.model_dump(),
        "currency": pl_data.currency,
        "displayLocale": pl_data.displayLocale,
        "sales_turnover": round(pl_data.sales_turnover, 2),
        "sales_food_beverage": round(pl_data.sales_food_beverage, 2),
        "sales_delivery": round(pl_data.sales_delivery, 2),
        "cogs_food_beverage": round(pl_data.cogs_food_beverage, 2),
        "cogs_raw_waste": round(pl_data.cogs_raw_waste, 2),
        "cogs_total": round(cogs_total, 2),
        "opex_non_food": round(pl_data.opex_non_food, 2),
        "opex_platforms": round(pl_data.opex_platforms, 2),
        "opex_total": round(opex_total, 2),
        "labour_employees": round(pl_data.labour_employees, 2),
        "labour_staff_meal": round(pl_data.labour_staff_meal, 2),
        "labour_total": round(labour_total, 2),
        "marketing_online_ads": round(pl_data.marketing_online_ads, 2),
        "marketing_free_items": round(pl_data.marketing_free_items, 2),
        "marketing_total": round(marketing_total, 2),
        "rent_base_effective": round(pl_data.rent_base_effective, 2),
        "rent_garden": round(pl_data.rent_garden, 2),
        "rent_total": round(rent_total, 2),
        "other_total": round(pl_data.other_total, 2),
        "kpi_ebitda": round(ebitda, 2),
        "notes": pl_data.notes,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "updatedAt": None
    }
    
    await db.pl_snapshots.insert_one(snapshot)
    
    # Log audit
    await log_audit(
        db,
        current_user["restaurantId"],
        "pl_snapshot",
        "create",
        current_user["id"],
        {"period": f"{pl_data.period.start} to {pl_data.period.end}", "ebitda": ebitda}
    )
    
    snapshot.pop("_id", None)
    return PLSnapshot(**snapshot)

@api_router.get("/pl/snapshot", response_model=List[PLSnapshot])
async def get_pl_snapshots(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get P&L snapshots, optionally filtered by date range"""
    await check_subscription(current_user)
    
    query = {"restaurantId": current_user["restaurantId"]}
    
    if start_date or end_date:
        query["period.start"] = {}
        if start_date:
            query["period.start"]["$gte"] = start_date
        if end_date:
            query["period.start"]["$lte"] = end_date
    
    snapshots = await db.pl_snapshots.find(query, {"_id": 0}).sort("period.start", -1).to_list(1000)
    return [PLSnapshot(**s) for s in snapshots]

# ============ P&L ROUTES (LEGACY) ============

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

from fastapi import Form
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
    fileType: str = Form(None),  # Optional: 'price_list', 'contract', 'general'
    current_user: dict = Depends(get_current_user)
):
    """Attach a file to a supplier"""
    await check_subscription(current_user)
    
    # RBAC: Only admin and manager can upload files
    if current_user["roleKey"] not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Only administrators and managers can upload files")
    
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
            "fileType": fileType or "general",  # price_list, contract, general
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
            {"filename": file.filename, "fileType": fileType}
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
    
    # RBAC: Only admin and manager can create receiving records
    if current_user["roleKey"] not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Only administrators and managers can create receiving records")
    
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
    try:
        await check_subscription(current_user)
        
        receiving_records = await db.receiving.find(
            {"restaurantId": current_user["restaurantId"]},
            {"_id": 0}
        ).sort("arrivedAt", -1).to_list(1000)
        
        logger.info(f"Found {len(receiving_records)} receiving records")
        
        # Convert to Receiving objects
        result = []
        for r in receiving_records:
            try:
                result.append(Receiving(**r))
            except Exception as e:
                logger.error(f"Error serializing receiving record {r.get('id', 'unknown')}: {e}")
                logger.error(f"Record data: {r}")
                # Continue with other records
        
        return result
    except Exception as e:
        logger.error(f"Error in get_receiving: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

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
    
    # RBAC: Only admin and manager can update receiving records
    if current_user["roleKey"] not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Only administrators and managers can update receiving records")
    
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
    
    # RBAC: Only admin and manager can delete receiving records
    if current_user["roleKey"] not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Only administrators and managers can delete receiving records")
    
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
@api_router.get("/ingredients/{ingredient_id}/price-history")
async def get_ingredient_price_history(
    ingredient_id: str,
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """Get price history for an ingredient from receiving records"""
    await check_subscription(current_user)
    
    # Get ingredient to verify it exists
    ingredient = await db.ingredients.find_one({
        "id": ingredient_id,
        "restaurantId": current_user["restaurantId"]
    }, {"_id": 0})
    
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    
    # Query receiving records that contain this ingredient
    receiving_records = await db.receiving.find({
        "restaurantId": current_user["restaurantId"],
        "lines.ingredientId": ingredient_id
    }, {"_id": 0}).sort("arrivedAt", -1).limit(limit * 3).to_list(limit * 3)
    
    # Extract price history
    price_history = []
    for record in receiving_records:
        for line in record.get("lines", []):
            if line.get("ingredientId") == ingredient_id:
                price_history.append({
                    "date": record.get("arrivedAt"),
                    "unitPrice": line.get("unitPrice"),
                    "qty": line.get("qty"),
                    "unit": line.get("unit"),
                    "packFormat": line.get("packFormat"),
                    "supplierId": record.get("supplierId"),
                    "supplierName": None  # Will be populated below
                })
    
    # Limit to requested number
    price_history = price_history[:limit]
    
    # Populate supplier names
    supplier_ids = list(set([ph["supplierId"] for ph in price_history if ph.get("supplierId")]))
    if supplier_ids:
        suppliers = await db.suppliers.find(
            {"id": {"$in": supplier_ids}},
            {"_id": 0, "id": 1, "name": 1}
        ).to_list(len(supplier_ids))
        supplier_map = {s["id"]: s["name"] for s in suppliers}
        
        for ph in price_history:
            if ph.get("supplierId"):
                ph["supplierName"] = supplier_map.get(ph["supplierId"])
    
    return {
        "ingredientId": ingredient_id,
        "ingredientName": ingredient["name"],
        "history": price_history
    }

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


# ============================================================================
# OCR / Document Ingestion Endpoints (Phase 8)
# ============================================================================

@api_router.post("/ocr/process")
async def process_document_ocr(
    file: UploadFile = File(...),
    lang: str = 'eng',
    current_user: dict = Depends(get_current_user)
):
    """
    Process document with OCR and extract structured data
    Supports images and PDFs
    """
    await check_subscription(current_user)
    
    # RBAC: Only admin and manager can process documents
    if current_user["roleKey"] not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Only administrators and managers can process documents")
    
    try:
        from ocr_service import get_ocr_service
        from document_parser import get_parser
        
        # Read file content
        file_content = await file.read()
        file_extension = file.filename.split('.')[-1].lower()
        
        # Validate file type
        supported_types = ['jpg', 'jpeg', 'png', 'pdf', 'tiff', 'bmp']
        if file_extension not in supported_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type. Supported: {', '.join(supported_types)}"
            )
        
        # Save to temp file for processing
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_extension}') as temp_file:
            temp_file.write(file_content)
            temp_path = temp_file.name
        
        try:
            # Run OCR
            ocr_service = get_ocr_service(lang=lang)
            ocr_result = ocr_service.extract_text(temp_path, file_extension, lang=lang)
            
            if not ocr_result.get('success'):
                raise HTTPException(status_code=500, detail=f"OCR failed: {ocr_result.get('error')}")
            
            # Parse extracted text
            parser = get_parser()
            parsed_data = parser.auto_parse(ocr_result['text'])
            
            # Return combined results
            return {
                "success": True,
                "filename": file.filename,
                "ocr": {
                    "text": ocr_result['text'],
                    "confidence": ocr_result.get('confidence', 0),
                    "language": ocr_result.get('language'),
                    "page_count": ocr_result.get('page_count', 1)
                },
                "parsed": parsed_data
            }
            
        finally:
            # Clean up temp file
            import os
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OCR processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Document processing failed: {str(e)}")


@api_router.post("/ocr/save-mappings")
async def save_ocr_mappings(
    mapping_data: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """
    Save OCR ingredient mappings for future use
    Maps description patterns to ingredient IDs
    """
    await check_subscription(current_user)
    
    try:
        supplier_id = mapping_data.get('supplierId')
        mappings = mapping_data.get('mappings', [])  # [{ description, ingredientId, code }]
        
        # Upsert mappings for this supplier
        for mapping in mappings:
            description = mapping.get('description', '').lower().strip()
            ingredient_id = mapping.get('ingredientId')
            code = mapping.get('code', '')
            
            if not description or not ingredient_id:
                continue
            
            # Check if mapping exists
            existing = await db.ocr_mappings.find_one({
                "restaurantId": current_user["restaurantId"],
                "supplierId": supplier_id,
                "description": description
            })
            
            if existing:
                # Update existing
                await db.ocr_mappings.update_one(
                    {"_id": existing["_id"]},
                    {
                        "$set": {
                            "ingredientId": ingredient_id,
                            "code": code,
                            "updatedAt": datetime.now(timezone.utc).isoformat(),
                            "updatedBy": current_user["email"]
                        }
                    }
                )
            else:
                # Create new
                await db.ocr_mappings.insert_one({
                    "id": str(uuid.uuid4()),
                    "restaurantId": current_user["restaurantId"],
                    "supplierId": supplier_id,
                    "description": description,
                    "ingredientId": ingredient_id,
                    "code": code,
                    "createdAt": datetime.now(timezone.utc).isoformat(),
                    "createdBy": current_user["email"],
                    "useCount": 0
                })
        
        return {"message": "Mappings saved", "count": len(mappings)}
        
    except Exception as e:
        logger.error(f"Error saving OCR mappings: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to save mappings")


@api_router.get("/ocr/mappings/{supplier_id}")
async def get_ocr_mappings(
    supplier_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get saved OCR mappings for a supplier
    Returns: { description -> ingredientId } map
    """
    await check_subscription(current_user)
    
    try:
        mappings = await db.ocr_mappings.find({
            "restaurantId": current_user["restaurantId"],
            "supplierId": supplier_id
        }, {"_id": 0}).to_list(1000)
        
        # Increment use count
        for mapping in mappings:
            await db.ocr_mappings.update_one(
                {"id": mapping["id"]},
                {"$inc": {"useCount": 1}}
            )
        
        return {
            "mappings": mappings,
            "count": len(mappings)
        }
        
    except Exception as e:
        logger.error(f"Error fetching OCR mappings: {str(e)}")
        return {"mappings": [], "count": 0}


@api_router.post("/ocr/create-receiving")
async def create_receiving_from_ocr(
    document_data: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """
    Create receiving record from OCR-parsed document
    User must review and confirm before this is called (NO SILENT IMPORTS)
    """
    await check_subscription(current_user)
    
    # RBAC: Only admin and manager can create receiving from OCR
    if current_user["roleKey"] not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Only administrators and managers can import documents")
    
    try:
        # Extract data from parsed document
        supplier_id = document_data.get('supplierId')
        if not supplier_id:
            raise HTTPException(status_code=400, detail="Supplier ID is required")
        
        # Verify supplier exists
        supplier = await db.suppliers.find_one({
            "id": supplier_id,
            "restaurantId": current_user["restaurantId"]
        })
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")
        
        # Build receiving record
        receiving_id = str(uuid.uuid4())
        line_items = document_data.get('lineItems', [])
        
        # Validate and process line items
        processed_lines = []
        for item in line_items:
            ingredient_id = item.get('ingredientId')
            if not ingredient_id:
                continue  # Skip unmapped items
            
            # Verify ingredient exists
            ingredient = await db.ingredients.find_one({
                "id": ingredient_id,
                "restaurantId": current_user["restaurantId"]
            })
            if not ingredient:
                continue
            
            processed_lines.append({
                "ingredientId": ingredient_id,
                "description": item.get('description', ingredient['name']),
                "qty": float(item.get('qty', 0)),
                "unit": item.get('unit', ingredient['unit']),
                "unitPrice": float(item.get('unitPrice', 0)),
                "packFormat": item.get('packFormat', ''),
                "expiryDate": item.get('expiryDate', '')
            })
        
        if not processed_lines:
            raise HTTPException(status_code=400, detail="No valid line items to import")
        
        # Prepare attached files array (if original document provided)
        attached_files = []
        if document_data.get('originalDocumentUrl'):
            attached_files.append({
                "fileId": str(uuid.uuid4()),
                "filename": document_data.get('originalFilename', 'ocr_document.pdf'),
                "downloadUrl": document_data.get('originalDocumentUrl'),
                "uploadedAt": datetime.now(timezone.utc).isoformat(),
                "fileType": "ocr_invoice"
            })
        
        # Calculate total from line items (in minor units)
        total_amount = sum(line["qty"] * line["unitPrice"] for line in processed_lines)
        
        # Create receiving record
        receiving_data = {
            "id": receiving_id,
            "restaurantId": current_user["restaurantId"],
            "supplierId": supplier_id,
            "category": document_data.get('category', 'food'),
            "arrivedAt": document_data.get('date') or datetime.now(timezone.utc).strftime('%Y-%m-%d'),
            "lines": processed_lines,
            "total": total_amount,
            "files": attached_files,
            "notes": f"Imported from OCR - {document_data.get('documentType', 'invoice')} | Confidence: {document_data.get('confidence', 0)}%",
            "invoiceNumber": document_data.get('invoiceNumber'),
            "importedFromOCR": True,  # Flag for UI display
            "ocrMetadata": {
                "confidence": document_data.get('confidence', 0),
                "documentType": document_data.get('documentType'),
                "processedAt": datetime.now(timezone.utc).isoformat()
            },
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "createdBy": current_user["email"]
        }
        
        await db.receiving.insert_one(receiving_data)
        
        # Update inventory for each line item
        for line in processed_lines:
            ingredient = await db.ingredients.find_one({"id": line["ingredientId"]})
            if not ingredient:
                continue
            
            # Calculate cost in minor units
            qty_in_base_unit = line["qty"]
            unit_cost_minor = int(line["unitPrice"] * 100)
            total_cost_minor = int(qty_in_base_unit * unit_cost_minor)
            
            # Update or create inventory record
            existing_inventory = await db.inventory.find_one({
                "restaurantId": current_user["restaurantId"],
                "ingredientId": line["ingredientId"]
            })
            
            if existing_inventory:
                # WAC calculation
                old_qty = existing_inventory["qtyOnHand"]
                old_value = existing_inventory["totalValue"]
                new_qty = old_qty + qty_in_base_unit
                new_value = old_value + total_cost_minor
                new_unit_cost = int(new_value / new_qty) if new_qty > 0 else unit_cost_minor
                
                await db.inventory.update_one(
                    {"_id": existing_inventory["_id"]},
                    {
                        "$set": {
                            "qtyOnHand": new_qty,
                            "unitCost": new_unit_cost,
                            "totalValue": new_value,
                            "lastUpdated": datetime.now(timezone.utc).isoformat()
                        }
                    }
                )
            else:
                # Create new inventory record
                await db.inventory.insert_one({
                    "id": str(uuid.uuid4()),
                    "restaurantId": current_user["restaurantId"],
                    "ingredientId": line["ingredientId"],
                    "qtyOnHand": qty_in_base_unit,
                    "unit": line["unit"],
                    "unitCost": unit_cost_minor,
                    "totalValue": total_cost_minor,
                    "lastUpdated": datetime.now(timezone.utc).isoformat()
                })
        
        # Log audit trail
        await log_audit(
            db=db,
            restaurant_id=current_user["restaurantId"],
            user_id=current_user["id"],
            action="create_receiving_from_ocr",
            entity_type="receiving",
            entity_id=receiving_id,
            details={
                "supplierId": supplier_id,
                "lineCount": len(processed_lines),
                "documentType": document_data.get('documentType'),
                "invoiceNumber": document_data.get('invoiceNumber'),
                "ocrConfidence": document_data.get('confidence', 0)
            }
        )
        
        receiving_data.pop("_id", None)
        return Receiving(**receiving_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating receiving from OCR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create receiving: {str(e)}")

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
                
                # Calculate recipe cost (supports both ingredients and preparations)
                recipe_cost = 0
                for item in recipe.get("items", []):
                    if item.get("type") == "ingredient" or "ingredientId" in item:
                        # New format or legacy format
                        item_id = item.get("itemId") or item.get("ingredientId")
                        ingredient = ingredients_map.get(item_id)
                        if ingredient:
                            effective_cost = ingredient.get("effectiveUnitCost", ingredient["unitCost"])
                            ingredient_unit = ingredient.get("unit", "kg")
                            item_qty = item["qtyPerPortion"]
                            item_unit = item.get("unit", ingredient_unit)
                            
                            # Normalize quantity to ingredient's unit
                            normalized_qty = normalize_quantity_to_base_unit(item_qty, item_unit, ingredient_unit)
                            recipe_cost += round(effective_cost * normalized_qty, 4)
                    elif item.get("type") == "preparation":
                        # Preparation cost (already includes ingredient costs with waste)
                        prep = await db.preparations.find_one({"id": item["itemId"]}, {"_id": 0})
                        if prep:
                            recipe_cost += prep.get("cost", 0) * item["qtyPerPortion"]
                
                total_cogs += recipe_cost * qty
    
    food_cost_pct = (total_cogs / total_revenue * 100) if total_revenue > 0 else 0
    
    # Low stock items - use qtyOnHand from Phase 1 inventory structure
    low_stock_count = 0
    for ing in ingredients:
        # Find current inventory for this ingredient
        inv_record = next((inv for inv in inventory if inv.get("ingredientId") == ing["id"]), None)
        current_qty = inv_record.get("qtyOnHand", 0) if inv_record else 0
        
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


# ==================== RBAC ENDPOINTS ====================

from rbac_schema import (
    DEFAULT_PERMISSIONS,
    Resource,
    Action,
    get_default_permissions,
    has_permission,
    merge_permissions
)
from rbac_middleware import get_user_permissions, get_user_capabilities


@api_router.get("/rbac/capabilities/{resource}")
async def get_resource_capabilities(
    resource: str,
    current_user: dict = Depends(get_current_user)
):
    """Get user's capabilities for a specific resource"""
    capabilities = await get_user_capabilities(current_user, db, resource)
    return capabilities


@api_router.get("/rbac/roles")
async def get_rbac_roles(current_user: dict = Depends(get_current_user)):
    """Get all roles with their default permissions"""
    # Only admins can access RBAC
    if current_user["roleKey"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get restaurant-specific permission overrides
    restaurant = await db.restaurants.find_one(
        {"id": current_user["restaurantId"]},
        {"_id": 0, "permissionOverrides": 1}
    )
    
    overrides = restaurant.get("permissionOverrides", {}) if restaurant else {}
    
    # Build role list with merged permissions
    roles = []
    for role_key, default_perms in DEFAULT_PERMISSIONS.items():
        role_overrides = overrides.get(role_key, {})
        merged_perms = merge_permissions(default_perms, role_overrides)
        
        roles.append({
            "roleKey": role_key,
            "roleName": role_key.capitalize(),
            "permissions": merged_perms,
            "isCustomized": bool(role_overrides)
        })
    
    return roles


@api_router.get("/rbac/resources")
async def get_rbac_resources(current_user: dict = Depends(get_current_user)):
    """Get all available resources and actions"""
    # Only admins can access RBAC
    if current_user["roleKey"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    resources = [
        {
            "key": resource.value,
            "name": resource.value.replace("_", " ").title(),
            "actions": [action.value for action in Action]
        }
        for resource in Resource
    ]
    
    return resources


@api_router.put("/rbac/roles/{role_key}/permissions")
async def update_role_permissions(
    role_key: str,
    permissions: Dict[str, List[str]],
    current_user: dict = Depends(get_current_user)
):
    """Update permissions for a specific role"""
    # Only admins can modify RBAC
    if current_user["roleKey"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Validate role exists
    if role_key not in DEFAULT_PERMISSIONS:
        raise HTTPException(status_code=404, detail=f"Role {role_key} not found")
    
    # Validate all resources and actions
    valid_resources = {r.value for r in Resource}
    valid_actions = {a.value for a in Action}
    
    for resource, actions in permissions.items():
        if resource not in valid_resources:
            raise HTTPException(status_code=400, detail=f"Invalid resource: {resource}")
        for action in actions:
            if action not in valid_actions:
                raise HTTPException(status_code=400, detail=f"Invalid action: {action}")
    
    # Update restaurant's permission overrides
    await db.restaurants.update_one(
        {"id": current_user["restaurantId"]},
        {"$set": {f"permissionOverrides.{role_key}": permissions}}
    )
    
    # Audit log
    await log_audit(
        db=db,
        restaurant_id=current_user["restaurantId"],
        user_id=current_user["id"],
        action="update",
        entity_type="rbac_permissions",
        entity_id=role_key,
        details={"permissions": permissions}
    )
    
    return {"success": True, "message": f"Permissions updated for role {role_key}"}


@api_router.post("/rbac/roles/{role_key}/reset")
async def reset_role_permissions(
    role_key: str,
    current_user: dict = Depends(get_current_user)
):
    """Reset role permissions to defaults"""
    # Only admins can modify RBAC
    if current_user["roleKey"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Validate role exists
    if role_key not in DEFAULT_PERMISSIONS:
        raise HTTPException(status_code=404, detail=f"Role {role_key} not found")
    
    # Remove override for this role
    await db.restaurants.update_one(
        {"id": current_user["restaurantId"]},
        {"$unset": {f"permissionOverrides.{role_key}": ""}}
    )
    
    # Audit log
    await log_audit(
        db=db,
        restaurant_id=current_user["restaurantId"],
        user_id=current_user["id"],
        action="reset",
        entity_type="rbac_permissions",
        entity_id=role_key,
        details={"reset_to": "defaults"}
    )
    
    return {"success": True, "message": f"Permissions reset to defaults for role {role_key}"}


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
    """Shutdown database connection"""
    mongo_client.close()
