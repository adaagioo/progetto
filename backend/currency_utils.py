"""
Currency utilities for multi-currency support
Stores amounts in minor units (cents/centesimi) as integers
"""

CURRENCY_CONFIG = {
    "EUR": {"symbol": "€", "decimals": 2, "minorUnit": 100},
    "USD": {"symbol": "$", "decimals": 2, "minorUnit": 100}
}

# Static exchange rates (EUR base)
EXCHANGE_RATES = {
    "EUR": 1.0,
    "USD": 1.08
}

def to_minor_units(amount: float, currency_code: str = "EUR") -> int:
    """Convert decimal amount to minor units (cents)
    
    Args:
        amount: Decimal amount (e.g., 8.50)
        currency_code: Currency code (EUR, USD)
    
    Returns:
        Integer in minor units (e.g., 850)
    """
    config = CURRENCY_CONFIG.get(currency_code, {"minorUnit": 100})
    return int(round(amount * config["minorUnit"]))

def from_minor_units(amount: int, currency_code: str = "EUR") -> float:
    """Convert minor units to decimal amount
    
    Args:
        amount: Amount in minor units (e.g., 850)
        currency_code: Currency code (EUR, USD)
    
    Returns:
        Decimal amount (e.g., 8.50)
    """
    config = CURRENCY_CONFIG.get(currency_code, {"minorUnit": 100})
    return amount / config["minorUnit"]

def format_amount(amount: int, currency_code: str, locale: str = "en-US") -> dict:
    """Format amount for API response with locale-aware formatting
    
    Args:
        amount: Amount in minor units
        currency_code: Currency code
        locale: Locale for formatting (e.g., it-IT, en-US)
    
    Returns:
        Dict with value, currency, decimal, and formatted string
    """
    decimal_amount = from_minor_units(amount, currency_code)
    config = CURRENCY_CONFIG.get(currency_code, {"symbol": "$", "decimals": 2})
    
    # Use locale-specific formatting
    if locale.startswith("it"):
        # Italian format: € 8,50
        formatted = f"{config['symbol']} {decimal_amount:,.{config['decimals']}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    else:
        # English format: $8.50
        formatted = f"{config['symbol']}{decimal_amount:,.{config['decimals']}f}"
    
    return {
        "value": amount,
        "currency": currency_code,
        "decimal": decimal_amount,
        "formatted": formatted
    }

def parse_decimal_input(input_str: str, currency_code: str = "EUR") -> int:
    """Parse user input string to minor units
    
    Args:
        input_str: User input like "8.50" or "8,50"
        currency_code: Currency code
    
    Returns:
        Amount in minor units
    """
    # Normalize comma/dot for decimal separator
    normalized = input_str.replace(",", ".")
    try:
        decimal_amount = float(normalized)
        return to_minor_units(decimal_amount, currency_code)
    except ValueError:
        raise ValueError(f"Invalid amount format: {input_str}")

def convert_currency(amount: int, from_currency: str, to_currency: str) -> int:
    """Convert amount between currencies using exchange rates
    
    Args:
        amount: Amount in minor units
        from_currency: Source currency code
        to_currency: Target currency code
    
    Returns:
        Converted amount in minor units
    """
    if from_currency == to_currency:
        return amount
    
    # Convert to EUR base
    decimal_amount = from_minor_units(amount, from_currency)
    eur_amount = decimal_amount / EXCHANGE_RATES.get(from_currency, 1.0)
    
    # Convert to target currency
    target_amount = eur_amount * EXCHANGE_RATES.get(to_currency, 1.0)
    return to_minor_units(target_amount, to_currency)

def get_currency_config(currency_code: str = "EUR") -> dict:
    """Get currency configuration
    
    Args:
        currency_code: Currency code
    
    Returns:
        Currency config dict
    """
    return CURRENCY_CONFIG.get(currency_code, CURRENCY_CONFIG["EUR"])

