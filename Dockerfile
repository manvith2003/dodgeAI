# Use Python 3.10 slim as the base image
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Copy the backend requirements file
COPY backend/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire backend directory into the container
COPY backend/ ./backend/

# Expose port (Hugging Face Spaces default to 7860)
EXPOSE 7860

# Start the FastAPI server using Uvicorn
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
