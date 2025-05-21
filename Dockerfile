# Dockerfile

# Stage 1: Use an official Python runtime as a parent image
# Using python 3.11 slim-buster for a smaller image size
FROM python:3.11-slim-buster AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1 # Prevents python from writing .pyc files
ENV PYTHONUNBUFFERED 1       # Prevents python from buffering stdout/stderr

# Set the working directory in the container
WORKDIR /app

# Install system dependencies if needed (e.g., for certain Python packages)
# RUN apt-get update && apt-get install -y --no-install-recommends some-package && rm -rf /var/lib/apt/lists/*
# (Currently, none seem strictly necessary based on requirements.txt, but keep in mind)

# Install Python dependencies
# First copy only requirements.txt to leverage Docker cache
COPY requirements.txt .

# Upgrade pip and install requirements
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root user to run the application
RUN useradd -m appuser
USER appuser

# Copy the application code into the container
# Ensure the non-root user owns the files
COPY --chown=appuser:appuser ./app /app/app

# Expose the port the app runs on
# Make sure this matches the port used in the CMD instruction
EXPOSE 8001

# Define the command to run the application
# Use 0.0.0.0 to make it accessible outside the container
# Do NOT use --reload in production images
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]