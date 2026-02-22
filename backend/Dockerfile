FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for caching
COPY backend/requirements.txt /app/backend/requirements.txt

# Install dependencies (no PyTorch needed - using FastEmbed/ONNX instead)
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy backend code and data
COPY backend/ /app/backend/

# Set Python path
ENV PYTHONPATH=/app

# Pre-download the FastEmbed ONNX model during build
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', cache_dir='/app/models_cache')"

# Build the vector database during image build
RUN python -c "import sys; sys.path.insert(0,'/app'); from backend.tools.setup_db import setup_database; setup_database()"

# Clean up to reduce image size
RUN rm -rf /root/.cache /tmp/*

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
