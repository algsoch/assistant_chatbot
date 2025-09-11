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
COPY templates/ templates/
COPY static/ static/

# Create necessary directories
RUN mkdir -p uploads temp_files

# Expose port
EXPOSE 8000

# Run the application
CMD ["gunicorn", "vicky_app:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "120"]