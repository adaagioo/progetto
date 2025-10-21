"""
File Storage Service with pluggable drivers.
Currently supports local storage; S3/GCS can be added later.
"""
import os
import hashlib
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime
from abc import ABC, abstractmethod

# Optional import for file type detection
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False


class StorageDriver(ABC):
    """Abstract storage driver interface"""
    
    @abstractmethod
    async def save(self, file_data: bytes, filename: str, subfolder: str = "") -> str:
        """Save file and return storage path"""
        pass
    
    @abstractmethod
    async def read(self, path: str) -> bytes:
        """Read file from storage"""
        pass
    
    @abstractmethod
    async def delete(self, path: str) -> bool:
        """Delete file from storage"""
        pass
    
    @abstractmethod
    def get_url(self, path: str) -> str:
        """Get URL for file access"""
        pass


class LocalStorageDriver(StorageDriver):
    """Local filesystem storage driver"""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    async def save(self, file_data: bytes, filename: str, subfolder: str = "") -> str:
        """Save file to local filesystem"""
        # Create subfolder if needed
        target_dir = self.base_path / subfolder
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        name_parts = os.path.splitext(filename)
        unique_filename = f"{name_parts[0]}_{timestamp}{name_parts[1]}"
        
        # Full path
        file_path = target_dir / unique_filename
        
        # Write file
        with open(file_path, "wb") as f:
            f.write(file_data)
        
        # Return relative path from base
        return str(Path(subfolder) / unique_filename)
    
    async def read(self, path: str) -> bytes:
        """Read file from local filesystem"""
        file_path = self.base_path / path
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        with open(file_path, "rb") as f:
            return f.read()
    
    async def delete(self, path: str) -> bool:
        """Delete file from local filesystem"""
        file_path = self.base_path / path
        if file_path.exists():
            file_path.unlink()
            return True
        return False
    
    def get_url(self, path: str) -> str:
        """Return API path for file (to be served via auth route)"""
        return f"/api/files/{path}"


class StorageService:
    """Main storage service with validation and metadata handling"""
    
    def __init__(self, driver: StorageDriver, max_size_mb: int, allowed_mimes: str):
        self.driver = driver
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.allowed_mimes = set(mime.strip() for mime in allowed_mimes.split(","))
    
    def validate_file(self, file_data: bytes, filename: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate file by size, MIME type, and magic bytes.
        Returns: (is_valid, mime_type, error_message)
        """
        # Check size
        if len(file_data) > self.max_size_bytes:
            return False, None, f"File too large (max {self.max_size_bytes // (1024*1024)}MB)"
        
        # Detect MIME type using magic bytes if available
        try:
            if MAGIC_AVAILABLE:
                mime_type = magic.from_buffer(file_data, mime=True)
            else:
                # Fallback: accept common types without validation
                mime_type = "application/octet-stream"
        except Exception as e:
            return False, None, f"Could not detect file type: {str(e)}"
        
        # Check if allowed (skip if magic not available)
        if MAGIC_AVAILABLE and mime_type not in self.allowed_mimes:
            return False, mime_type, f"File type not allowed: {mime_type}"
        
        return True, mime_type, None
    
    def compute_hash(self, file_data: bytes) -> str:
        """Compute SHA256 hash of file"""
        return hashlib.sha256(file_data).hexdigest()
    
    async def save_file(
        self,
        file_data: bytes,
        filename: str,
        subfolder: str = ""
    ) -> dict:
        """
        Save file with validation and return metadata.
        Returns: {
            "path": str,
            "filename": str,
            "size": int,
            "mime_type": str,
            "hash": str,
            "url": str
        }
        """
        # Validate
        is_valid, mime_type, error = self.validate_file(file_data, filename)
        if not is_valid:
            raise ValueError(error)
        
        # Compute hash
        file_hash = self.compute_hash(file_data)
        
        # Save to storage
        storage_path = await self.driver.save(file_data, filename, subfolder)
        
        # Return metadata
        return {
            "path": storage_path,
            "filename": filename,
            "size": len(file_data),
            "mime_type": mime_type,
            "hash": file_hash,
            "url": self.driver.get_url(storage_path)
        }
    
    async def read_file(self, path: str) -> bytes:
        """Read file from storage"""
        return await self.driver.read(path)
    
    async def delete_file(self, path: str) -> bool:
        """Delete file from storage"""
        return await self.driver.delete(path)


# Global storage service instance
_storage_service: Optional[StorageService] = None


def init_storage_service(
    driver_type: str = "local",
    base_path: str = "/app/uploads",
    max_size_mb: int = 10,
    allowed_mimes: str = ""
) -> StorageService:
    """Initialize storage service with given configuration"""
    global _storage_service
    
    if driver_type == "local":
        driver = LocalStorageDriver(base_path)
    else:
        raise ValueError(f"Unsupported storage driver: {driver_type}")
    
    _storage_service = StorageService(driver, max_size_mb, allowed_mimes)
    return _storage_service


def get_storage_service() -> StorageService:
    """Get initialized storage service"""
    if _storage_service is None:
        raise RuntimeError("Storage service not initialized. Call init_storage_service() first.")
    return _storage_service
