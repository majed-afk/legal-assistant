FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for caching
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy backend code and data
COPY backend/ /app/backend/

# Set Python path so "from backend.xxx import yyy" works
ENV PYTHONPATH=/app

# Build the vector database
RUN python -c "import sys; sys.path.insert(0,'/app'); from backend.tools.setup_db import setup_database; setup_database()"

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
