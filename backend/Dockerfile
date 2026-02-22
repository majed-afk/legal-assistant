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

# Build vector DB at image build time using Gemini Embedding API
# Render auto-injects env vars as Docker build args
ARG GOOGLE_API_KEY
RUN if [ -n "$GOOGLE_API_KEY" ]; then \
      GOOGLE_API_KEY=$GOOGLE_API_KEY python -m backend.tools.setup_db; \
    else \
      echo "⚠️  GOOGLE_API_KEY not set — skipping DB build"; \
    fi

# Clean up to reduce image size
RUN rm -rf /root/.cache /tmp/*

EXPOSE 8000

# Vector DB is pre-built during image build (765 articles)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
