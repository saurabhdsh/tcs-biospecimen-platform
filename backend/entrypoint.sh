#!/bin/sh
set -e

echo "Running database migrations..."
alembic upgrade head

if [ "${SEED_ON_START:-true}" = "true" ]; then
  echo "Seeding database if empty..."
  python -m app.seed
fi

echo "Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
