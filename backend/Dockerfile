# Backend Dockerfile
FROM python:3.11-slim-bookworm

# Install system dependencies including libmagic and WeasyPrint requirements
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libmagic1 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libfribidi0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    libcairo2 \
    libgirepository-1.0-1 \
    fonts-liberation \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy requirements first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Set ownership
RUN chown -R appuser:appuser /app

# Create upload directory
RUN mkdir -p /tmp/analyzer-uploads && chown appuser:appuser /tmp/analyzer-uploads

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
