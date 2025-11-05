# Multi-stage Docker build for production
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libmagic1 \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd -m -u 1000 -s /bin/bash permia

WORKDIR /app


# Builder stage
FROM base as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies
RUN pip install --user --no-warn-script-location -e .


# Production stage
FROM base as production

# Copy Python packages from builder
COPY --from=builder /root/.local /home/permia/.local

# Copy application code
COPY --chown=permia:permia src ./src
COPY --chown=permia:permia migrations ./migrations
COPY --chown=permia:permia alembic.ini ./
COPY --chown=permia:permia keys ./keys

# Switch to non-root user
USER permia

# Update PATH
ENV PATH=/home/permia/.local/bin:$PATH

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5).raise_for_status()" || exit 1

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
