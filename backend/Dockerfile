FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for asyncpg
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy project config
COPY pyproject.toml ./

# Install dependencies with pip (uv is also fine, but pip keeps the image simpler)
RUN pip install --no-cache-dir -e ".[dev,rag]" || pip install --no-cache-dir .

# Copy application code
COPY app/ ./app/
COPY data/ ./data/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
