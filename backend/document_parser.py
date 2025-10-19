"""
Document Parsing Pipeline
Extracts structured data from OCR text (invoices, price lists)
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DocumentParser:
    """Parse structured data from OCR-extracted text"""
    
    def __init__(self):
        # Common patterns for invoice/price list parsing
        self.date_patterns = [
            r'(?:date|data):\s*(\d{4}-\d{2}-\d{2})',
            r'(?:date|data):\s*(\d{2}/\d{2}/\d{4})',
            r'(?:date|data):\s*(\d{2}\.\d{2}\.\d{4})',
            r'(\d{4}-\d{2}-\d{2})',
            r'(\d{2}/\d{2}/\d{4})'
        ]
        
        self.invoice_number_patterns = [
            r'(?:invoice|fattura|inv)[\s#:]*([A-Z0-9-]+)',
            r'(?:n\.?|no\.?)[\s:]*([A-Z0-9-]+)'
        ]
        
        self.vat_patterns = [
            r'(?:vat|p\.?iva|partita iva)[\s:]*([A-Z]{2}[0-9]{8,12})',
            r'([A-Z]{2}[0-9]{11})'
        ]
        
        self.total_patterns = [
            r'(?:total|totale|subtotal)[\s:]*€?\s*([0-9,]+\.?\d{2})',
            r'(?:total|totale|subtotal)[\s:]*\$\s*([0-9,]+\.?\d{2})',
            r'€?\s*([0-9,]+\.?\d{2})\s*(?:total|totale)'
        ]
    
    def parse_invoice_number(self, text: str) -> Optional[str]:
        """Extract invoice number"""
        # Try Italian patterns first
        italian_patterns = [
            r'(?:Fattura|Invoice|Documento).*?(?:numero|n\.|#)\s*(\d+)',
            r'(?:numero|n\.|#)\s*(\d+)',
        ]
        
        for pattern in italian_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Try original patterns
        for pattern in self.invoice_number_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None
    
    def parse_date(self, text: str) -> Optional[str]:
        """Extract and normalize date from text"""
        text_lower = text.lower()
        
        # Add Italian date pattern: 26.09.2025
        date_patterns = [
            r'(\d{2}\.\d{2}\.\d{4})',  # DD.MM.YYYY (Italian)
            r'(\d{2}/\d{2}/\d{4})',    # DD/MM/YYYY
            r'(\d{4}-\d{2}-\d{2})',    # YYYY-MM-DD
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                date_str = match.group(1)
                try:
                    # Try different date formats
                    for fmt in ['%d.%m.%Y', '%d/%m/%Y', '%Y-%m-%d']:
                        try:
                            dt = datetime.strptime(date_str, fmt)
                            return dt.strftime('%Y-%m-%d')
                        except ValueError:
                            continue
                except:
                    pass
        
        # Try original patterns
        for pattern in self.date_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                try:
                    # Try different date formats
                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d.%m.%Y']:
                        try:
                            dt = datetime.strptime(date_str, fmt)
                            return dt.strftime('%Y-%m-%d')
                        except ValueError:
                            continue
                except:
                    pass
        return None
    
    def parse_vat_number(self, text: str) -> Optional[str]:
        """Extract VAT/Tax ID number"""
        for pattern in self.vat_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None
    
    def parse_supplier_name(self, text: str) -> Optional[str]:
        """
        Extract supplier name (usually near the top of the document)
        This is a heuristic approach - takes first substantial line after header
        """
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Skip invoice number line
        for i, line in enumerate(lines):
            if re.search(r'invoice|fattura', line, re.IGNORECASE):
                # Supplier name often on next line or two
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    # Avoid lines with only numbers or VAT
                    if len(next_line) > 5 and not re.match(r'^[0-9\s\-\/]+$', next_line):
                        return next_line
        return None
    
    def parse_line_items(self, text: str, document_type: str = 'invoice') -> List[Dict[str, Any]]:
        """
        Extract line items from invoice or price list
        
        Args:
            text: OCR extracted text
            document_type: 'invoice' or 'price_list'
        
        Returns:
            List of parsed line items
        """
        lines = text.split('\n')
        items = []
        
        # Find the section with line items (after header/info)
        in_items_section = False
        item_header_found = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect item section start - improved for Italian invoices
            if re.search(r'\b(?:item|description|product|qty|quantity|price|prezzo|articolo|codice.*descrizione|gtà.*descrizione)\b', line, re.IGNORECASE):
                item_header_found = True
                in_items_section = True
                continue
            
            # Also detect by looking for product code pattern (L0347, V1933, etc.)
            if not in_items_section and re.match(r'^[A-Z]\d{4}\s+\d+', line):
                in_items_section = True
            
            # Stop at total or footer
            if re.search(r'\b(?:totale|subtotal|note|annotazioni|firma|assolve)\b', line, re.IGNORECASE):
                break
            
            if in_items_section:
                # Try to parse line item
                item = self._parse_single_line_item(line, document_type)
                if item:
                    items.append(item)
        
        return items
    
    def _parse_single_line_item(self, line: str, document_type: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single line item
        Expected formats:
        - Invoice: "Description Qty Unit Price"
        - Italian format: "CODE QTY\DESCRIPTION UNIT %IVA | UM PRICE PRICE"
        - Price list: "Product Code Price Unit"
        """
        # Italian invoice pattern: "L0347 1\AMARO DEL CAPO 1LT 22 | N 14,96 14,96"
        # Variations: 1\ or 1. or 1 or 6|
        italian_pattern = r'^([A-Z]\d{4})\s+(\d+)[\\.\s|]+(.+?)\s+(\d+)\s+\|\s+\w+\s+([\d,]+(?:\.?\d+)?)\s+([\d,]+(?:\.?\d+)?)$'
        match = re.match(italian_pattern, line)
        if match:
            code, qty, description, iva, unit_price, total = match.groups()
            # Clean up description (remove size info at end if present)
            desc_clean = re.sub(r'\s+(1LT|70CL\.?|75CL\.?|ML|LT|KG|G|\d+CL\.?)$', '', description.strip(), flags=re.IGNORECASE)
            
            return {
                "description": desc_clean.strip(),
                "qty": float(qty),
                "unit": self._extract_unit_from_description(description) or 'unit',
                "price": float(unit_price.replace(',', '.')),
                "code": code,
                "line_text": line
            }
        
        # Generic pattern: capture description, numbers, and currency
        # Example: "San Marzano Tomatoes 10.0 kg €3.40"
        
        # Try to extract components
        parts = line.split()
        if len(parts) < 3:
            return None
        
        # Find numbers and currency
        numbers = []
        description_parts = []
        unit = None
        price = None
        
        for i, part in enumerate(parts):
            # Check if it's a number (qty or price)
            if re.match(r'^[0-9]+\.?[0-9]*$', part):
                numbers.append(float(part))
            # Check if it's a price with currency
            elif re.match(r'^[€$£]?[0-9,]+\.?\d{0,2}$', part):
                price_str = re.sub(r'[€$£,]', '', part)
                try:
                    price = float(price_str)
                except:
                    pass
            # Check if it's a unit
            elif part.lower() in ['kg', 'g', 'l', 'ml', 'pcs', 'pz', 'unit', 'units', 'lt', 'cl']:
                unit = part.lower()
            # Otherwise it's part of description
            else:
                description_parts.append(part)
        
        # Need at least description and one number
        if not description_parts or not (numbers or price):
            return None
        
        description = ' '.join(description_parts)
        qty = numbers[0] if numbers else 1.0
        
        # If price not found in currency format, try last number
        if price is None and len(numbers) > 1:
            price = numbers[-1]
        
        return {
            "description": description,
            "qty": qty,
            "unit": unit or 'unit',
            "price": price,
            "line_text": line  # Keep original for review
        }
    
    def _extract_unit_from_description(self, description: str) -> Optional[str]:
        """Extract unit from description text"""
        # Common Italian units
        units = {
            '1LT': 'L',
            'LT': 'L',
            '70CL': 'cl',
            '75CL': 'cl',
            'CL': 'cl',
            'ML': 'ml',
            'KG': 'kg',
            'G': 'g'
        }
        
        for pattern, unit in units.items():
            if pattern in description.upper():
                return unit
        
        return None
    
    def parse_invoice(self, ocr_text: str) -> Dict[str, Any]:
        """
        Parse invoice from OCR text
        
        Returns:
            Structured invoice data
        """
        return {
            "document_type": "invoice",
            "invoice_number": self.parse_invoice_number(ocr_text),
            "date": self.parse_date(ocr_text),
            "supplier_name": self.parse_supplier_name(ocr_text),
            "vat_number": self.parse_vat_number(ocr_text),
            "line_items": self.parse_line_items(ocr_text, document_type='invoice'),
            "total": self._extract_total(ocr_text),
            "raw_text": ocr_text
        }
    
    def parse_price_list(self, ocr_text: str) -> Dict[str, Any]:
        """
        Parse price list from OCR text
        
        Returns:
            Structured price list data
        """
        return {
            "document_type": "price_list",
            "supplier_name": self.parse_supplier_name(ocr_text),
            "date": self.parse_date(ocr_text),
            "items": self.parse_line_items(ocr_text, document_type='price_list'),
            "raw_text": ocr_text
        }
    
    def _extract_total(self, text: str) -> Optional[float]:
        """Extract total amount from invoice"""
        for pattern in self.total_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    total_str = match.group(1).replace(',', '')
                    return float(total_str)
                except:
                    pass
        return None
    
    def auto_parse(self, ocr_text: str) -> Dict[str, Any]:
        """
        Auto-detect document type and parse accordingly
        
        Returns:
            Parsed document data with document type
        """
        text_lower = ocr_text.lower()
        
        # Detect document type
        if re.search(r'\b(?:invoice|fattura|inv)\b', text_lower):
            return self.parse_invoice(ocr_text)
        elif re.search(r'\b(?:price list|listino prezzi|catalog)\b', text_lower):
            return self.parse_price_list(ocr_text)
        else:
            # Default to invoice parsing
            return self.parse_invoice(ocr_text)


# Singleton instance
_parser = None

def get_parser() -> DocumentParser:
    """Get or create document parser instance"""
    global _parser
    if _parser is None:
        _parser = DocumentParser()
    return _parser
