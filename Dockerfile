# Use an official lightweight Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables to optimize Python performance inside Docker
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies (build-essential needed for compiling any native extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch CPU-only first to prevent downloading heavy CUDA/Nvidia packages
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Copy requirements.txt first to leverage Docker's caching mechanism
COPY requirements.txt .

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files into the container
COPY . .

# Expose port 8000
EXPOSE 8000

# Set environment variables for the application (will default to localhost if not specified in compose)
ENV REDIS_HOST=localhost
ENV REDIS_PORT=6379
ENV OLLAMA_HOST=http://localhost:11434

# Start the FastAPI server using Uvicorn
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
