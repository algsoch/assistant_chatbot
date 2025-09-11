# Use Python 3.11 base image
FROM python:3.11.7-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip==23.3.1 && \
    pip install --no-cache-dir setuptools==68.2.2 wheel==0.42.0 && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY vicky_app.py vicky_server.py vickys.json ./
COPY static/ static/
COPY docker-entrypoint.sh /usr/local/bin/

# Create necessary directories including writable templates
RUN mkdir -p uploads temp_files templates

# Copy templates to temporary location for later initialization
COPY templates/ /tmp/templates_source/

# Make entrypoint script executable
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Expose port
EXPOSE 8000

# Set entrypoint
ENTRYPOINT ["docker-entrypoint.sh"]

# Run the application
CMD ["gunicorn", "vicky_app:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "120"]