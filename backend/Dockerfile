FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for caching
COPY backend/requirements.txt /app/backend/requirements.txt

# Install dependencies (uses ONNX runtime — no PyTorch needed, ~200MB vs ~2GB)
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy backend code and data (articles.json + embeddings.json)
COPY backend/ /app/backend/

# Set Python path
ENV PYTHONPATH=/app

# Build ChromaDB from pre-computed embeddings (no API needed, ~5 seconds)
RUN python -c "from backend.tools.setup_db import setup_database; setup_database()"

# Clean up to reduce image size
RUN rm -rf /root/.cache /tmp/*

EXPOSE 8000

CMD ["gunicorn", "backend.main:app", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "120"]
