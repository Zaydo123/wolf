#!/bin/bash

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Set PYTHONPATH to the current directory
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Run the application
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 