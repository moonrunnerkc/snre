FROM python:3.11-slim

LABEL maintainer="SNRE Development Team"
LABEL description="Swarm Neural Refactoring Engine"
LABEL version="1.0.0"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data/refactor_logs data/snapshots logs

# Create non-root user for security
RUN groupadd -r snre && useradd -r -g snre snre
RUN chown -R snre:snre /app
USER snre

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/refactor/sessions || exit 1

# Expose API port
EXPOSE 8000

# Default command - start API server
CMD ["python", "main.py", "api", "0.0.0.0", "8000"]