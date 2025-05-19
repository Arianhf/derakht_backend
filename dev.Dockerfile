FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Add Django development server auto-reloading
RUN pip install --no-cache-dir watchdog

# Copy project
COPY . /app/

EXPOSE 8000

# Development entrypoint
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]