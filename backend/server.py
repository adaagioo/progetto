# server.py - Bridge file for Emergent deployment
# Imports the FastAPI app from main.py to match supervisor configuration
import sys
from pathlib import Path

# Add parent directory to path for 'backend' package resolution
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.main import app

__all__ = ["app"]
