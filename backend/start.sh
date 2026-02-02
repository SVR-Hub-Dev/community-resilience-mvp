#!/bin/bash
# Render startup script
cd /opt/render/project/src/backend
export PYTHONPATH=/opt/render/project/src/backend:$PYTHONPATH
exec uvicorn app:app --host 0.0.0.0 --port $PORT
