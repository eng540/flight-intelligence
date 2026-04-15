#!/bin/bash
set -e

echo "Running database migrations..."
cd /app/backend
alembic upgrade head

echo "Starting Celery worker..."
cd /app
celery -A worker.celery_app worker -l info -Q ingestion,maintenance,default &

echo "Starting Celery beat..."
celery -A worker.celery_app beat -l info &

echo "Starting FastAPI backend..."
cd /app/backend
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 4