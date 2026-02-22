FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for caching
COPY backend/requirements.txt /app/backend/requirements.txt

# Install dependencies (lightweight — no local ML models, uses Gemini API)
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy backend code and data (articles.json needed for DB build)
COPY backend/ /app/backend/

# Set Python path
ENV PYTHONPATH=/app

# Skip DB build at Docker build time — Gemini free tier rate limits
# make it unreliable. Runtime builds the DB incrementally with retries.

# Clean up to reduce image size
RUN rm -rf /root/.cache /tmp/*

EXPOSE 8000

# DB is built at runtime with resumable incremental builds
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
