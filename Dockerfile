FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run migrations and start server
CMD alembic upgrade head && uvicorn src.main:app --host 0.0.0.0 --port 8000
