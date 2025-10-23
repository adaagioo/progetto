#!/usr/bin/env python3
"""
Debug unit conversion function
"""

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
    """
    from_unit_lower = from_unit.lower()
    to_unit_lower = to_unit.lower()
    
    print(f"Converting {qty} {from_unit} to {to_unit}")
    print(f"from_unit_lower: {from_unit_lower}, to_unit_lower: {to_unit_lower}")
    
    # Same unit, no conversion needed
    if from_unit_lower == to_unit_lower:
        print("Same unit, no conversion")
        return qty
    
    # Get conversion factors
    from_factor = UNIT_CONVERSIONS.get(from_unit_lower)
    to_factor = UNIT_CONVERSIONS.get(to_unit_lower)
    
    print(f"from_factor: {from_factor}, to_factor: {to_factor}")
    
    # If either unit is unknown, return original (no conversion)
    if from_factor is None or to_factor is None:
        print("Unknown unit, no conversion")
        return qty
    
    # Convert: from_unit -> base_unit -> to_unit
    result = qty * from_factor / to_factor
    print(f"Conversion result: {qty} * {from_factor} / {to_factor} = {result}")
    return result

# Test cases
print("=== Testing Unit Conversions ===")
print()

# Test 1: 2g to kg
result1 = normalize_quantity_to_base_unit(2, 'g', 'kg')
print(f"Test 1: 2g to kg = {result1} (expected: 0.002)")
print()

# Test 2: 500ml to L
result2 = normalize_quantity_to_base_unit(500, 'ml', 'L')
print(f"Test 2: 500ml to L = {result2} (expected: 0.5)")
print()

# Test 3: 100mg to kg
result3 = normalize_quantity_to_base_unit(100, 'mg', 'kg')
print(f"Test 3: 100mg to kg = {result3} (expected: 0.0001)")
print()

# Test cost calculation
print("=== Testing Cost Calculation ===")
print()

# Cocoa: €10/kg, 2g
cocoa_unit_cost = 1000  # €10/kg in minor units
cocoa_qty_normalized = normalize_quantity_to_base_unit(2, 'g', 'kg')
cocoa_cost = cocoa_unit_cost * cocoa_qty_normalized
print(f"Cocoa cost: €{cocoa_unit_cost}/kg * {cocoa_qty_normalized}kg = €{cocoa_cost} (expected: €20 in minor units = €0.02)")
print()

# Vanilla: €4/L, 500ml
vanilla_unit_cost = 400  # €4/L in minor units
vanilla_qty_normalized = normalize_quantity_to_base_unit(500, 'ml', 'L')
vanilla_cost = vanilla_unit_cost * vanilla_qty_normalized
print(f"Vanilla cost: €{vanilla_unit_cost}/L * {vanilla_qty_normalized}L = €{vanilla_cost} (expected: €200 in minor units = €2.00)")