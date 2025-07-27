# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for PyMuPDF
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create input and output directories
RUN mkdir -p input output

# Copy the application code
COPY pdf_extractor.py .

# Set permissions
RUN chmod +x pdf_extractor.py

# Create a non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Run the application
CMD ["python", "pdf_extractor.py"]