FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for caching
COPY backend/requirements.txt /app/backend/requirements.txt

# Install CPU-only PyTorch first (saves ~1.5GB vs full CUDA torch)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install remaining dependencies
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy backend code and data
COPY backend/ /app/backend/

# Set Python path
ENV PYTHONPATH=/app

# Limit PyTorch threads to reduce memory
ENV OMP_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
ENV TORCH_NUM_THREADS=1

# Build the vector database during image build
RUN python -c "import sys; sys.path.insert(0,'/app'); from backend.tools.setup_db import setup_database; setup_database()"

# Clean up to reduce image size
RUN rm -rf /root/.cache /tmp/*

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
