# Use a Python base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy only necessary files
COPY vicky_app.py vicky_server.py vickys.json ./

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p templates static uploads

# Expose the port the app runs on
EXPOSE 8000

# Command to run the app
CMD ["python", "vicky_app.py"]