# Use official Python lightweight image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies (required for some Python packages like PyMuPDF)
RUN apt-get update && apt-get install -y \
    build-essential \
    libmupdf-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose port (Internal Container App traffic will route here)
EXPOSE 8000

# Start FastAPI app
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
