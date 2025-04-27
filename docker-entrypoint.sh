#!/bin/bash
set -e

# Function to wait for a service to be available
wait_for_service() {
  local SERVICE_HOST=$1
  local SERVICE_PORT=$2
  local SERVICE_NAME=$3
  
  echo "Waiting for $SERVICE_NAME at $SERVICE_HOST:$SERVICE_PORT to be available..."
  
  while ! nc -z $SERVICE_HOST $SERVICE_PORT; do
    echo "$SERVICE_NAME not available yet, sleeping..."
    sleep 2
  done
  
  echo "$SERVICE_NAME is available now!"
}

# Wait for MariaDB to be ready if the environment variables are set
if [ -n "$DB_HOST" ] && [ -n "$DB_PORT" ]; then
  wait_for_service $DB_HOST $DB_PORT "MariaDB"
fi

# Wait for Redis if it's used
if [ -n "$REDIS_HOST" ] && [ -n "$REDIS_PORT" ]; then
  wait_for_service $REDIS_HOST $REDIS_PORT "Redis"
fi

# Run database migrations if environment variable is set
if [ "${RUN_MIGRATIONS}" = "true" ]; then
  echo "Running database migrations..."
  python migrate_db.py --upgrade
fi

# Create Frappe site if it doesn't exist
if [ ! -f /app/sites/hrms.localhost/site_config.json ]; then
  echo "Creating Frappe site..."
  
  # Generate site config
  cat > /app/sites/hrms.localhost/site_config.json << EOF
{
  "db_name": "${DB_NAME:-hrms}",
  "db_host": "${DB_HOST:-mariadb}",
  "db_port": ${DB_PORT:-3306},
  "db_user": "${DB_USER:-frappe}",
  "db_password": "${DB_PASSWORD:-frappe_password}",
  "host_name": "${FRAPPE_SITE_NAME:-hrms.localhost}",
  "developer_mode": ${DEVELOPER_MODE:-0}
}
EOF
  
  # Apply migrations if needed
  python frappe_init.py --init-frappe-site
fi

# Create required directories if they don't exist
mkdir -p /app/logs
touch /app/logs/gunicorn.log
touch /app/logs/gunicorn_error.log

exec "$@"