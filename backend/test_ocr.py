#!/usr/bin/env python3
"""
Test OCR service with sample text
Creates a simple test image and verifies OCR extraction
"""

import sys
import os
from PIL import Image, ImageDraw, ImageFont

# Add backend to path
sys.path.insert(0, '/app/backend')

from ocr_service import get_ocr_service


def create_sample_invoice_image():
    """Create a simple invoice image for testing"""
    # Create a white image
    width, height = 800, 600
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    
    # Try to use a default font
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
        font_normal = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except:
        font_large = ImageFont.load_default()
        font_normal = ImageFont.load_default()
    
    # Invoice content
    y_pos = 50
    
    # Header
    draw.text((50, y_pos), "INVOICE #INV-2025-001", fill='black', font=font_large)
    y_pos += 40
    
    # Supplier info
    draw.text((50, y_pos), "Metro Cash & Carry", fill='black', font=font_normal)
    y_pos += 25
    draw.text((50, y_pos), "Via Roma 123, Milan", fill='black', font=font_normal)
    y_pos += 25
    draw.text((50, y_pos), "VAT: IT12345678901", fill='black', font=font_normal)
    y_pos += 40
    
    # Date
    draw.text((50, y_pos), "Date: 2025-10-19", fill='black', font=font_normal)
    y_pos += 40
    
    # Line items header
    draw.text((50, y_pos), "Item", fill='black', font=font_normal)
    draw.text((350, y_pos), "Qty", fill='black', font=font_normal)
    draw.text((450, y_pos), "Unit", fill='black', font=font_normal)
    draw.text((550, y_pos), "Price", fill='black', font=font_normal)
    y_pos += 30
    
    # Line items
    items = [
        ("San Marzano Tomatoes", "10.0", "kg", "€3.40"),
        ("Extra Virgin Olive Oil", "5.0", "L", "€12.00"),
        ("Parmigiano Reggiano", "2.5", "kg", "€28.00")
    ]
    
    for item, qty, unit, price in items:
        draw.text((50, y_pos), item, fill='black', font=font_normal)
        draw.text((350, y_pos), qty, fill='black', font=font_normal)
        draw.text((450, y_pos), unit, fill='black', font=font_normal)
        draw.text((550, y_pos), price, fill='black', font=font_normal)
        y_pos += 25
    
    y_pos += 20
    
    # Total
    draw.text((50, y_pos), "Total: €164.00", fill='black', font=font_large)
    
    return image


def test_ocr_service():
    """Test OCR service with sample invoice"""
    print("=" * 80)
    print("TESSERACT OCR SERVICE TEST")
    print("=" * 80)
    
    # Create sample invoice
    print("\n✓ Creating sample invoice image...")
    invoice_image = create_sample_invoice_image()
    
    # Save to temp file
    temp_path = "/tmp/test_invoice.png"
    invoice_image.save(temp_path)
    print(f"✓ Saved test invoice to {temp_path}")
    
    # Test OCR service
    print("\n✓ Initializing OCR service...")
    ocr = get_ocr_service(lang='eng')
    
    # Extract text
    print("✓ Extracting text from invoice...")
    result = ocr.extract_text_from_image(temp_path, lang='eng')
    
    # Display results
    print("\n" + "=" * 80)
    print("OCR RESULTS")
    print("=" * 80)
    print(f"Success: {result['success']}")
    print(f"Language: {result.get('language', 'N/A')}")
    print(f"Confidence: {result.get('confidence', 0)}%")
    print(f"\nExtracted Text:\n{'-' * 80}")
    print(result['text'])
    print("-" * 80)
    
    # Test Italian
    print("\n✓ Testing Italian language support...")
    result_it = ocr.extract_text_from_image(temp_path, lang='ita')
    print(f"Italian OCR Success: {result_it['success']}")
    print(f"Confidence: {result_it.get('confidence', 0)}%")
    
    # Verify key information extracted
    text = result['text'].lower()
    checks = [
        ("Invoice number", "inv-2025-001" in text),
        ("Supplier name", "metro" in text or "cash" in text),
        ("Date", "2025" in text or "date" in text),
        ("Item 1", "tomato" in text or "san marzano" in text),
        ("Item 2", "olive oil" in text or "oil" in text),
        ("Item 3", "parmigiano" in text or "reggiano" in text),
        ("Total", "164" in text or "total" in text)
    ]
    
    print("\n" + "=" * 80)
    print("VERIFICATION CHECKS")
    print("=" * 80)
    
    passed = 0
    for check_name, result in checks:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {check_name}")
        if result:
            passed += 1
    
    print("\n" + "=" * 80)
    print(f"FINAL RESULT: {passed}/{len(checks)} checks passed")
    print("=" * 80)
    
    if passed >= len(checks) * 0.7:  # 70% pass rate
        print("\n🎉 OCR service is working correctly!")
        return True
    else:
        print("\n⚠️  OCR service may need tuning")
        return False


if __name__ == "__main__":
    try:
        test_ocr_service()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
