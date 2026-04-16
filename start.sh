#!/bin/bash
set -e

echo "Running database migrations..."
cd /app/backend
PYTHONPATH="" alembic upgrade head

echo "Starting Celery worker..."
cd /app
export PYTHONPATH=/app/backend:/app
celery -A worker.celery_app worker -l info -Q ingestion,maintenance,default &

echo "Starting Celery beat..."
celery -A worker.celery_app beat -l info &

echo "Starting FastAPI backend..."
cd /app/backend
# تم تقليل العمال (workers) إلى 1 لمنع اختناق الذاكرة وتجمد الخادم
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1