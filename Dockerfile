FROM python:3.10-slim

# Install system dependencies required for psycopg2 and other packages
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

# Copy application code
COPY . .

# Create directory for instance/database if needed (though we use Postgres)
RUN mkdir -p instance

# Expose the port Gunicorn will run on
EXPOSE 5000

# Command to run the application
CMD ["gunicorn", "-c", "gunicorn_config.py", "app:create_app('production')"]
