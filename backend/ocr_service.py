"""
OCR Service using Tesseract
Handles text extraction from images and PDFs
"""

import pytesseract
from PIL import Image
from pdf2image import convert_from_path, convert_from_bytes
import io
import os
import logging
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import tempfile

logger = logging.getLogger(__name__)


class OCRService:
    """OCR service using Tesseract for text extraction"""
    
    def __init__(self, default_lang: str = 'eng'):
        """
        Initialize OCR service
        
        Args:
            default_lang: Default language for OCR (eng, ita, etc.)
        """
        self.default_lang = default_lang
        self.supported_languages = ['eng', 'ita']
        
        # Verify Tesseract installation
        try:
            version = pytesseract.get_tesseract_version()
            logger.info(f"Tesseract OCR initialized - version {version}")
        except Exception as e:
            logger.error(f"Tesseract not found or not properly installed: {e}")
            raise RuntimeError("Tesseract OCR is not available")
    
    def extract_text_from_image(
        self, 
        image_source: Union[str, bytes, Image.Image],
        lang: Optional[str] = None,
        config: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract text from an image
        
        Args:
            image_source: Path to image file, bytes, or PIL Image object
            lang: Language code (eng, ita). Defaults to default_lang
            config: Additional Tesseract config options
        
        Returns:
            Dict containing extracted text and metadata
        """
        try:
            # Load image
            if isinstance(image_source, str):
                image = Image.open(image_source)
            elif isinstance(image_source, bytes):
                image = Image.open(io.BytesIO(image_source))
            elif isinstance(image_source, Image.Image):
                image = image_source
            else:
                raise ValueError("Unsupported image source type")
            
            # Set language
            ocr_lang = lang or self.default_lang
            if ocr_lang not in self.supported_languages:
                logger.warning(f"Language {ocr_lang} not supported, falling back to {self.default_lang}")
                ocr_lang = self.default_lang
            
            # Extract text
            custom_config = config or '--psm 6'  # Assume uniform block of text
            text = pytesseract.image_to_string(image, lang=ocr_lang, config=custom_config)
            
            # Get additional data (confidence, boxes, etc.)
            data = pytesseract.image_to_data(image, lang=ocr_lang, output_type=pytesseract.Output.DICT)
            
            # Calculate average confidence
            confidences = [int(conf) for conf in data['conf'] if conf != '-1']
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            return {
                "success": True,
                "text": text.strip(),
                "language": ocr_lang,
                "confidence": round(avg_confidence, 2),
                "page_count": 1,
                "raw_data": data
            }
            
        except Exception as e:
            logger.error(f"Error extracting text from image: {e}")
            return {
                "success": False,
                "error": str(e),
                "text": ""
            }
    
    def extract_text_from_pdf(
        self,
        pdf_source: Union[str, bytes],
        lang: Optional[str] = None,
        max_pages: int = 10,
        dpi: int = 300
    ) -> Dict[str, Any]:
        """
        Extract text from a PDF by converting to images first
        
        Args:
            pdf_source: Path to PDF file or bytes
            lang: Language code
            max_pages: Maximum number of pages to process
            dpi: DPI for PDF to image conversion (higher = better quality, slower)
        
        Returns:
            Dict containing extracted text from all pages and metadata
        """
        try:
            # Convert PDF to images
            if isinstance(pdf_source, str):
                images = convert_from_path(pdf_source, dpi=dpi, first_page=1, last_page=max_pages)
            elif isinstance(pdf_source, bytes):
                images = convert_from_bytes(pdf_source, dpi=dpi, first_page=1, last_page=max_pages)
            else:
                raise ValueError("PDF source must be file path or bytes")
            
            all_text = []
            page_results = []
            total_confidence = 0
            
            for page_num, image in enumerate(images, start=1):
                result = self.extract_text_from_image(image, lang=lang)
                
                if result["success"]:
                    all_text.append(f"--- Page {page_num} ---\n{result['text']}")
                    page_results.append({
                        "page": page_num,
                        "text": result["text"],
                        "confidence": result["confidence"]
                    })
                    total_confidence += result["confidence"]
                else:
                    logger.warning(f"Failed to extract text from page {page_num}: {result.get('error')}")
            
            avg_confidence = total_confidence / len(images) if images else 0
            
            return {
                "success": True,
                "text": "\n\n".join(all_text),
                "language": lang or self.default_lang,
                "confidence": round(avg_confidence, 2),
                "page_count": len(images),
                "pages": page_results
            }
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            return {
                "success": False,
                "error": str(e),
                "text": ""
            }
    
    def extract_text(
        self,
        file_source: Union[str, bytes],
        file_type: str,
        lang: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Extract text from file (auto-detects image or PDF)
        
        Args:
            file_source: File path or bytes
            file_type: File extension (jpg, png, pdf, etc.)
            lang: Language code
            **kwargs: Additional options
        
        Returns:
            Dict containing extracted text and metadata
        """
        file_type = file_type.lower().lstrip('.')
        
        if file_type in ['jpg', 'jpeg', 'png', 'tiff', 'bmp', 'gif']:
            return self.extract_text_from_image(file_source, lang=lang)
        elif file_type == 'pdf':
            return self.extract_text_from_pdf(file_source, lang=lang, **kwargs)
        else:
            return {
                "success": False,
                "error": f"Unsupported file type: {file_type}"
            }


# Singleton instance
_ocr_service = None

def get_ocr_service(lang: str = 'eng') -> OCRService:
    """Get or create OCR service instance"""
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService(default_lang=lang)
    return _ocr_service
