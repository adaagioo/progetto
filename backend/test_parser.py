#!/usr/bin/env python3
"""
Test document parsing pipeline
"""

import sys
sys.path.insert(0, '/app/backend')

from backend.app.services.document_parser import get_parser


def test_invoice_parsing():
    """Test invoice parsing with sample OCR text"""
    
    # Sample OCR text from previous test
    sample_invoice = """
INVOICE #INV-2025-001

Metro Cash & Carry
Via Roma 123, Milan
VAT: IT12345678901

Date: 2025-10-19

Item Qty Unit Price
San Marzano Tomatoes 10.0 kg €3.40
Extra Virgin Olive Oil 5.0 L €12.00
Parmigiano Reggiano 2.5 kg €28.00

Total: €164.00
"""
    
    print("=" * 80)
    print("DOCUMENT PARSING PIPELINE TEST")
    print("=" * 80)
    
    print("\nSample Invoice Text:")
    print("-" * 80)
    print(sample_invoice)
    print("-" * 80)
    
    # Parse invoice
    parser = get_parser()
    result = parser.parse_invoice(sample_invoice)
    
    print("\n" + "=" * 80)
    print("PARSED RESULTS")
    print("=" * 80)
    
    print(f"\nDocument Type: {result['document_type']}")
    print(f"Invoice Number: {result['invoice_number']}")
    print(f"Date: {result['date']}")
    print(f"Supplier: {result['supplier_name']}")
    print(f"VAT Number: {result['vat_number']}")
    print(f"Total: €{result['total']}")
    
    print(f"\nLine Items ({len(result['line_items'])} items):")
    print("-" * 80)
    for i, item in enumerate(result['line_items'], 1):
        print(f"{i}. {item['description']}")
        print(f"   Qty: {item['qty']} {item['unit']}")
        print(f"   Price: €{item['price']}")
        print()
    
    # Verification
    print("=" * 80)
    print("VERIFICATION CHECKS")
    print("=" * 80)
    
    checks = [
        ("Invoice number extracted", result['invoice_number'] == 'INV-2025-001'),
        ("Date extracted", result['date'] == '2025-10-19'),
        ("Supplier name extracted", result['supplier_name'] is not None),
        ("VAT number extracted", result['vat_number'] == 'IT12345678901'),
        ("Total amount extracted", result['total'] == 164.00),
        ("Line items extracted", len(result['line_items']) >= 3)
    ]
    
    passed = 0
    for check_name, passed_check in checks:
        status = "✅ PASS" if passed_check else "❌ FAIL"
        print(f"{status}: {check_name}")
        if passed_check:
            passed += 1
    
    print("\n" + "=" * 80)
    print(f"FINAL RESULT: {passed}/{len(checks)} checks passed")
    print("=" * 80)
    
    if passed >= len(checks) * 0.8:  # 80% pass rate
        print("\n🎉 Document parsing is working correctly!")
        return True
    else:
        print("\n⚠️  Document parsing needs improvement")
        return False


if __name__ == "__main__":
    try:
        test_invoice_parsing()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
