FROM python:3.12-slim

# System deps (build for bcrypt if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

# Install only runtime requirements
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app/backend

# Create a non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app

# Create storage directory with correct permissions
RUN mkdir -p /data/storage && chown -R appuser:appuser /data

USER appuser

EXPOSE 8000

# Default storage path (bind a volume at runtime)
ENV STORAGE_LOCAL_PATH=/data/storage

# Start
CMD [ "sh", "/app/backend/run.sh" ]
