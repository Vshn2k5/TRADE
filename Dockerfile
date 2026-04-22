# APEX INDIA — Docker Configuration
# ====================================
# Multi-stage build for production deployment.
# Optimized for Mumbai VPS with low-latency NSE access.

FROM python:3.11-slim AS base

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libffi-dev libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/models

# Environment
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Kolkata

# Health check
HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
    CMD python -c "from apex_india.utils.config import ConfigLoader; print('OK')" || exit 1

# Default: paper trading mode
CMD ["python", "scheduler.py", "--mode", "paper"]
