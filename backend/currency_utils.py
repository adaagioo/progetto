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

def to_minor_units(amount: float, currency_code: str) -> int:
    """Convert decimal amount to minor units (cents)"""
    config = CURRENCY_CONFIG.get(currency_code, {"minorUnit": 100})
    return int(round(amount * config["minorUnit"]))

def from_minor_units(amount: int, currency_code: str) -> float:
    """Convert minor units to decimal amount"""
    config = CURRENCY_CONFIG.get(currency_code, {"minorUnit": 100})
    return amount / config["minorUnit"]

def format_amount(amount: int, currency_code: str, locale: str = "en-US") -> dict:
    """Format amount for API response"""
    decimal_amount = from_minor_units(amount, currency_code)
    config = CURRENCY_CONFIG.get(currency_code, {"symbol": "$", "decimals": 2})
    
    return {
        "value": amount,
        "currency": currency_code,
        "decimal": decimal_amount,
        "formatted": f"{config['symbol']}{decimal_amount:,.{config['decimals']}f}"
    }

def convert_currency(amount: int, from_currency: str, to_currency: str) -> int:
    """Convert amount between currencies using exchange rates"""
    if from_currency == to_currency:
        return amount
    
    # Convert to EUR base
    decimal_amount = from_minor_units(amount, from_currency)
    eur_amount = decimal_amount / EXCHANGE_RATES.get(from_currency, 1.0)
    
    # Convert to target currency
    target_amount = eur_amount * EXCHANGE_RATES.get(to_currency, 1.0)
    return to_minor_units(target_amount, to_currency)
