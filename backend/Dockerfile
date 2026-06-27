FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV WORKDIR=/app

WORKDIR $WORKDIR

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    g++ \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy and install dependencies
COPY requirements.txt $WORKDIR/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy backend application
COPY . $WORKDIR/

# Create data storage directories
RUN mkdir -p $WORKDIR/data/uploads $WORKDIR/data/vector_store

# Expose port
EXPOSE 8000

# Start script
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
