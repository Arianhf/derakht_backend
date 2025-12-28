FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN mkdir /app
# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r /app/requirements.txt


# Copy project
COPY . /app/

# Create logs directory to prevent StatReloader restart loop
RUN mkdir -p /app/logs

# Create user for security
RUN adduser --disabled-password --no-create-home django

# Give ownership to the django user
RUN chown -R django:django /app

# Switch to django user
USER django

EXPOSE 80

CMD ["bash", "entrypoint"]