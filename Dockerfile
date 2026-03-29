FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create credentials directory if not present
RUN mkdir -p /app/credentials

# Non-root user for safety
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Entry point
CMD ["python", "app.py"]
