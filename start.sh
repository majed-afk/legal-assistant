#!/bin/bash
# Start script for Render deployment
export PYTHONPATH=$(pwd)
exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
