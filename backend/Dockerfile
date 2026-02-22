FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for caching
COPY backend/requirements.txt /app/backend/requirements.txt

# Install dependencies (lightweight — no local ML models, uses Gemini API)
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy backend code and data
COPY backend/ /app/backend/

# Set Python path
ENV PYTHONPATH=/app

# Clean up to reduce image size
RUN rm -rf /root/.cache /tmp/*

EXPOSE 8000

# Vector DB is pre-built and shipped with the image (765 articles, ~17MB)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
