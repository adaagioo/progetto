"""
File upload utilities for handling attachments
Local storage implementation (can be swapped for S3/GCS later)
"""

import os
import uuid
from pathlib import Path
from typing import List, Optional
import shutil

# Configuration
UPLOAD_DIR = Path("/app/uploads")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {'.pdf', '.xlsx', '.xls', '.csv', '.doc', '.docx', '.jpg', '.jpeg', '.png'}
ALLOWED_MIME_TYPES = {
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-excel',
    'text/csv',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'image/jpeg',
    'image/png'
}

# Ensure upload directory exists
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def save_upload_file(file_content: bytes, filename: str, restaurant_id: str, category: str = "general") -> dict:
    """
    Save uploaded file to local storage
    
    Args:
        file_content: File bytes
        filename: Original filename
        restaurant_id: Restaurant ID for isolation
        category: File category (invoices, price_lists, etc.)
    
    Returns:
        Dict with file metadata
    """
    # Validate file extension
    file_ext = Path(filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"File type {file_ext} not allowed")
    
    # Validate file size
    if len(file_content) > MAX_FILE_SIZE:
        raise ValueError(f"File size exceeds {MAX_FILE_SIZE / 1024 / 1024}MB limit")
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    safe_filename = f"{file_id}{file_ext}"
    
    # Create restaurant-specific directory
    restaurant_dir = UPLOAD_DIR / restaurant_id / category
    restaurant_dir.mkdir(parents=True, exist_ok=True)
    
    # Save file
    file_path = restaurant_dir / safe_filename
    with open(file_path, 'wb') as f:
        f.write(file_content)
    
    # Return metadata
    return {
        "id": file_id,
        "originalName": filename,
        "filename": safe_filename,
        "path": str(file_path),
        "size": len(file_content),
        "extension": file_ext,
        "category": category,
        "url": f"/uploads/{restaurant_id}/{category}/{safe_filename}"
    }

def delete_file(file_path: str) -> bool:
    """Delete file from storage"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception as e:
        print(f"Error deleting file: {e}")
        return False

def get_file_url(restaurant_id: str, category: str, filename: str) -> str:
    """Get public URL for file"""
    return f"/uploads/{restaurant_id}/{category}/{filename}"
