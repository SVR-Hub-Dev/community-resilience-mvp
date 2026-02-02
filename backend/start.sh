#!/bin/bash
# Render startup script
# Add backend directory to Python path before starting
export PYTHONPATH=/opt/render/project/src/backend:$PYTHONPATH
cd /opt/render/project/src/backend
python -m uvicorn app:app --host 0.0.0.0 --port $PORT
