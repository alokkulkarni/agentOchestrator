# Model Gateway Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project (needed for imports)
COPY . /app/

# Create logs directory
RUN mkdir -p /app/model_gateway/logs

# Expose port
EXPOSE 8585

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8585/ || exit 1

# Set Python path
ENV PYTHONPATH=/app

# Run the gateway
CMD ["python3", "-m", "model_gateway.server"]
