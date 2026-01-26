# Backend API service
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
# Note: OrcaSlicer is not included in Docker due to cross-platform complexity.
# 3MF download requires OrcaSlicer to be installed on the host or set ORCASLICER_PATH.
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/*.py .
COPY backend/profiles ./profiles

# Environment variables
ENV REDIS_HOST=redis
ENV REDIS_PORT=6379
ENV MAPS_DIR=/data/maps
ENV PYTHONUNBUFFERED=1

# Create data directory
RUN mkdir -p /data/maps

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
