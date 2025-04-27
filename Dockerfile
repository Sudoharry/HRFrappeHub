FROM python:3.11-slim

LABEL maintainer="HR Management System Team <team@hrms.example.com>"
LABEL description="HR Management System based on Frappe/ERPNext"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    default-libmysqlclient-dev \
    libffi-dev \
    libjpeg-dev \
    libldap2-dev \
    libsasl2-dev \
    libtiff5-dev \
    libwebp-dev \
    libxml2-dev \
    libxslt1-dev \
    mariadb-client \
    nodejs \
    npm \
    redis-tools \
    tzdata \
    wkhtmltopdf \
    zlib1g-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy package definition
COPY pyproject.toml /app/
COPY uv.lock /app/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir poetry
RUN poetry config virtualenvs.create false
RUN poetry install
RUN pip install --no-cache-dir mysqlclient gunicorn gevent redis

# Copy application code
COPY . /app/

# Install node dependencies and build assets (if applicable)
RUN if [ -f package.json ]; then npm install && npm run build; fi

# Set environment variables
ENV FLASK_APP=app_frappe.py
ENV FLASK_ENV=production
ENV FLASK_DEBUG=0
ENV PYTHONUNBUFFERED=1
ENV FRAPPE_ENV=production

# Create directory for Frappe site
RUN mkdir -p /app/sites/hrms.localhost/public /app/sites/hrms.localhost/private \
    && chmod -R 775 /app/sites

# Setup entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Expose the port
EXPOSE 5000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/api/method/ping || exit 1

# Run the application
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["gunicorn", "--workers=4", "--worker-class=gevent", "--bind", "0.0.0.0:5000", "--timeout", "120", "--preload", "app_frappe:app"]