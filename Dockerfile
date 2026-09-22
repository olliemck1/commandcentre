FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY backend/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ /app/

# Environment defaults (Railway dynamically provides PORT)
ENV PORT=8000
EXPOSE 8000

# Start FastAPI uvicorn bound to Railway's dynamic $PORT
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
