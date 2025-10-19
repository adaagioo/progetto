"""
Allergen taxonomy utilities for EU-14 compliance
Provides normalization mapping to maintain backward compatibility
"""

# EU-14 Official Allergen Names
EU14_ALLERGENS = [
    "Cereals containing gluten",
    "Crustaceans",
    "Eggs",
    "Fish",
    "Peanuts",
    "Soybeans",
    "Milk",
    "Nuts",
    "Celery",
    "Mustard",
    "Sesame seeds",
    "Sulphur dioxide and sulphites",
    "Lupin",
    "Molluscs"
]

# Backward compatibility mapping (legacy → EU-14)
ALLERGEN_MAPPING = {
    # Legacy names to normalized EU-14
    "gluten": "Cereals containing gluten",
    "wheat": "Cereals containing gluten",
    "dairy": "Milk",
    "lactose": "Milk",
    "soy": "Soybeans",
    "shellfish": "Crustaceans",  # Default to crustaceans
    "sulfites": "Sulphur dioxide and sulphites",
    "tree nuts": "Nuts",
    
    # Already normalized (case-insensitive)
    "cereals containing gluten": "Cereals containing gluten",
    "crustaceans": "Crustaceans",
    "eggs": "Eggs",
    "fish": "Fish",
    "peanuts": "Peanuts",
    "soybeans": "Soybeans",
    "milk": "Milk",
    "nuts": "Nuts",
    "celery": "Celery",
    "mustard": "Mustard",
    "sesame seeds": "Sesame seeds",
    "sesame": "Sesame seeds",
    "sulphur dioxide and sulphites": "Sulphur dioxide and sulphites",
    "lupin": "Lupin",
    "molluscs": "Molluscs",
    "mollusks": "Molluscs",  # US spelling
}

def normalize_allergen(allergen: str) -> str:
    """
    Normalize an allergen name to EU-14 standard
    
    Args:
        allergen: Input allergen name (legacy or normalized)
        
    Returns:
        Normalized EU-14 allergen name
    """
    if not allergen:
        return allergen
    
    # Try case-insensitive mapping
    allergen_lower = allergen.lower().strip()
    
    if allergen_lower in ALLERGEN_MAPPING:
        return ALLERGEN_MAPPING[allergen_lower]
    
    # If already in EU-14 list (case-sensitive check)
    if allergen in EU14_ALLERGENS:
        return allergen
    
    # Return as-is if no mapping found (backward compatibility)
    return allergen

def normalize_allergen_list(allergens: list) -> list:
    """
    Normalize a list of allergens to EU-14 standard
    Removes duplicates and sorts alphabetically
    
    Args:
        allergens: List of allergen names
        
    Returns:
        Sorted list of normalized EU-14 allergen names
    """
    if not allergens:
        return []
    
    normalized = set()
    for allergen in allergens:
        if allergen:
            normalized.add(normalize_allergen(allergen))
    
    return sorted(list(normalized))

def get_allergen_display_name(allergen: str, locale: str = 'en') -> str:
    """
    Get localized display name for an allergen
    
    Args:
        allergen: Normalized EU-14 allergen name
        locale: Language code (en/it)
        
    Returns:
        Localized allergen display name
    """
    # Normalize first
    normalized = normalize_allergen(allergen)
    
    # Italian translations for EU-14 allergens
    if locale.lower() == 'it':
        IT_ALLERGENS = {
            "Cereals containing gluten": "Cereali contenenti glutine",
            "Crustaceans": "Crostacei",
            "Eggs": "Uova",
            "Fish": "Pesce",
            "Peanuts": "Arachidi",
            "Soybeans": "Soia",
            "Milk": "Latte",
            "Nuts": "Frutta a guscio",
            "Celery": "Sedano",
            "Mustard": "Senape",
            "Sesame seeds": "Semi di sesamo",
            "Sulphur dioxide and sulphites": "Anidride solforosa e solfiti",
            "Lupin": "Lupini",
            "Molluscs": "Molluschi"
        }
        return IT_ALLERGENS.get(normalized, normalized)
    
    return normalized

def validate_allergen(allergen: str) -> bool:
    """
    Check if an allergen is valid (can be normalized to EU-14)
    
    Args:
        allergen: Allergen name to validate
        
    Returns:
        True if valid/normalizable, False otherwise
    """
    if not allergen:
        return False
    
    normalized = normalize_allergen(allergen)
    return normalized in EU14_ALLERGENS or allergen.lower() in ALLERGEN_MAPPING
