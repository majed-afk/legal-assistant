#!/bin/bash
# Build script for Render deployment
set -e

echo "📦 Installing Python dependencies..."
pip install -r backend/requirements.txt

echo "🔧 Building vector database..."
PYTHONPATH=$(pwd) python -c "from backend.tools.setup_db import setup_database; setup_database()"

echo "✅ Build complete!"
