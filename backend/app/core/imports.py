"""
Central module to handle Python path setup and import resolution.
Import this module at the top of any file that needs to import modules from different directories.
"""
import os
import sys
import logging

logger = logging.getLogger(__name__)

# Get key directory paths
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # app/
BACKEND_DIR = os.path.dirname(APP_DIR)  # backend/

# Add both directories to Python path
for path in [BACKEND_DIR, APP_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)
        logger.debug(f"Added {path} to Python path")

# Export directories for use in other modules
__all__ = ['APP_DIR', 'BACKEND_DIR'] 