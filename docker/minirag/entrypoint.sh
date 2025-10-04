#!/bin/bash
set -e

# Log database host for easier debugging
echo "POSTGRES_HOST: $POSTGRES_HOST"
echo "Running database migrations..."

cd /app/models/db_schemas/minirag/
alembic upgrade head
cd /app

# Hand control back to the container CMD (uvicorn by default)
exec "$@"
