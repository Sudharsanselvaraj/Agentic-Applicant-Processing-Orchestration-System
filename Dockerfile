FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN pip install playwright && playwright install chromium --with-deps

# Copy application code
COPY . .

# Create data directories for persistence
RUN mkdir -p /app/data /app/logs /app/output /app/cache

# Default environment variables
ENV PYTHONPATH=/app
ENV LOOP_INTERVAL_SECONDS=300

# Volume for persistent data (cookies, token.pickle, db)
VOLUME ["/app/data", "/app/logs", "/app/output"]

# Expose API port
EXPOSE 8000

# Run the orchestrator
CMD ["python", "orchestrator.py"]