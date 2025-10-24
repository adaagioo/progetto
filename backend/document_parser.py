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
        """Extract invoice number - enhanced for Italian invoices"""
        # Italian patterns - "Fattura Accompagnatora ; 33124 26.09.2025"
        italian_patterns = [
            r'Fattura\s+Accompagnatora\s*[;:]\s*(\d+)',
            r'(?:Fattura|Invoice|Documento).*?(?:numero|n\.|#)\s*[:\s]*(\d+)',
            r'(?:numero|n\.|#)\s*[:\s]*(\d+)',
            r'(?:N\.\s*)?(\d{5,})',  # 5+ digit number (common for invoices)
        ]
        
        for pattern in italian_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                inv_num = match.group(1).strip()
                # Validate it's not a VAT or phone number
                if len(inv_num) <= 10 and not re.match(r'^0[36]', inv_num):  # Not phone
                    return inv_num
        
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
        Enhanced for Italian invoices
        """
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Italian pattern: look for "Destinatario" or customer name in caps
        # Supplier is typically the customer/recipient in transport documents
        for i, line in enumerate(lines):
            # Look for "Destinatario" section
            if re.search(r'Destinatario.*Intestazione', line, re.IGNORECASE):
                # Next line often contains the company name
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    # Check if it looks like a company name (all caps, ends with SRL/SPA/etc)
                    if re.match(r'^[A-Z\s]{3,}(?:SRL|SPA|S\.R\.L\.|S\.P\.A\.|S\.N\.C\.|S\.A\.S\.)?$', next_line):
                        return next_line
        
        # Alternative: look for company names with SRL, SPA, etc.
        company_pattern = r'([A-Z][A-Z\s]{3,}(?:SRL|SPA|S\.R\.L\.|S\.P\.A\.|S\.N\.C\.|S\.A\.S\.))'
        match = re.search(company_pattern, text)
        if match:
            return match.group(1).strip()
        
        # Fallback to original logic
        for i, line in enumerate(lines):
            if re.search(r'invoice|fattura', line, re.IGNORECASE):
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
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
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect item section start - improved for Italian invoices
            # Look for product code pattern (L0347, V1933, etc.) to start section
            if not in_items_section and re.match(r'^[A-Z]\d{4}\s+\d+', line):
                in_items_section = True
            
            # Also detect by header keywords
            if re.search(r'\b(?:codice.*descrizione|gtà.*descrizione)\b', line, re.IGNORECASE):
                in_items_section = True
                continue  # Skip header line
            
            # Stop at total or footer
            if re.search(r'\b(?:totale.*imponibile|annotazioni|firma|assolve|imponibile)\b', line, re.IGNORECASE):
                break
            
            if in_items_section:
                # Try to parse line item
                item = self._parse_single_line_item(line, document_type)
                if item:
                    items.append(item)
        
        return items
    
    def _parse_single_line_item(self, line: str, document_type: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single line item - enhanced for Italian invoices
        Expected formats:
        - Italian: "L0347 1 AMARO DEL CAPO 1LT 22 | N 14,96 14,96"
        - Italian: "V1933 6 VINO CHARDONNAY ATTEMS 2023 75CL 22 | N 7,2373 43,42"
        - Generic: "Description Qty Unit Price"
        """
        
        # Enhanced Italian invoice pattern
        # Format: CODE QTY DESCRIPTION SIZE IVA% | UM UNIT_PRICE LINE_TOTAL
        # Example: "L0347 1 AMARO DEL CAPO 1LT 22 | N 14,96 14,96"
        italian_patterns = [
            # With pipe separator
            r'^([A-Z]\d{4})\s+(\d+)\s+(.+?)\s+(\d{2})\s*\|\s*\w+\s+([\d,]+(?:\.?\d*)?)\s+([\d,]+(?:\.?\d*)?)$',
            # With comma in qty (12, SP.TOSO BRUT...)
            r'^([A-Z]\d{4})\s+(\d+),?\s+(.+?)\s+(\d{2})\s*\|\s*\w+\s+([\d,]+(?:\.?\d*)?)\s+([\d,]+(?:\.?\d*)?)$',
        ]
        
        for pattern in italian_patterns:
            match = re.match(pattern, line)
            if match:
                code, qty, description, iva, unit_price, total = match.groups()
                
                # Clean quantity (remove trailing comma if present)
                qty_clean = qty.rstrip(',')
                
                # Extract unit from description (1LT, 75CL, etc.)
                unit = self._extract_unit_from_description(description) or 'unit'
                
                # Clean description - remove size info at end
                desc_clean = re.sub(r'\s+(1LT|70CL\.?|75CL\.?|ML|LT|KG|G|\d+CL\.?|2023|2024|doc)$', '', description.strip(), flags=re.IGNORECASE)
                desc_clean = desc_clean.strip()
                
                # Convert comma decimals to dots
                unit_price_float = float(unit_price.replace(',', '.'))
                total_float = float(total.replace(',', '.'))
                
                return {
                    "description": desc_clean,
                    "qty": float(qty_clean),
                    "unit": unit,
                    "unit_price": unit_price_float,
                    "line_total": total_float,
                    "code": code,
                    "vat_percent": int(iva),
                    "line_text": line
                }
        
        # Generic pattern: capture description, numbers, and currency
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
            "unit_price": price,
            "line_text": line
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
        """Extract total amount from invoice - enhanced for Italian format"""
        # Italian pattern: "Totale Documento\n€ 268,23"
        italian_patterns = [
            r'Totale\s+Documento\s*[:\s]*€?\s*([\d,]+(?:\.?\d{2})?)',
            r'(?:importo\s+)?totale\s*[:\s]*€?\s*([\d,]+(?:\.?\d{2})?)',
        ]
        
        for pattern in italian_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    total_str = match.group(1).replace(',', '.')  # Italian uses comma for decimals
                    return float(total_str)
                except:
                    pass
        
        # Try original patterns
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
