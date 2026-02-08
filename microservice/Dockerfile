FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY microservice/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY microservice /app/microservice

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8001

# Run application
CMD ["uvicorn", "microservice.main:app", "--host", "0.0.0.0", "--port", "8001"]
