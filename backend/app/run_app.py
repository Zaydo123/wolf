#!/usr/bin/env python
import os
import sys
import uvicorn

# Add the parent directory to Python path first so we can import from app.core
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Now import from the central imports module
from app.core.imports import APP_DIR, BACKEND_DIR

if __name__ == "__main__":
    print("Starting Wolf backend from app directory...")
    print(f"Python path includes: {BACKEND_DIR} and {APP_DIR}")
    
    # When running from app directory, use "main:app" not "app.main:app"
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 