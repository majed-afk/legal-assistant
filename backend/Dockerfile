# ---- Stage 1: Builder (install deps + pre-build DB) ----
FROM python:3.11-slim AS builder

WORKDIR /app

# Copy requirements first for Docker layer caching
COPY backend/requirements.txt /app/backend/requirements.txt

# Install PyTorch CPU-only first (much smaller than default GPU version: ~200MB vs ~2GB)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install remaining dependencies
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy backend code and data (articles.json + embeddings.json)
COPY backend/ /app/backend/

# Set Python path
ENV PYTHONPATH=/app

# Pre-download the sentence-transformers model during build (cached in image)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"

# Build ChromaDB from pre-computed embeddings (no API needed, ~5 seconds)
RUN python -c "from backend.tools.setup_db import setup_database; setup_database()"

# Clean pip cache to reduce image size (keep model cache!)
RUN rm -rf /root/.cache/pip /tmp/*

# ---- Stage 2: Runtime ----
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy installed packages and built artifacts from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app
COPY --from=builder /root/.cache/torch /root/.cache/torch

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

CMD ["gunicorn", "backend.main:app", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "120", "--preload"]
