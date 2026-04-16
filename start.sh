#!/bin/bash
set -e

echo "Running database migrations..."
cd /app/backend
PYTHONPATH="" alembic upgrade head

echo "Starting Celery worker..."
cd /app
export PYTHONPATH=/app/backend:/app
# تم تحديد عدد العمال بـ 2 فقط لمنع اختناق قاعدة البيانات
celery -A worker.celery_app worker -l info -Q ingestion,maintenance,default --concurrency=2 &

echo "Starting Celery beat..."
celery -A worker.celery_app beat -l info &

echo "Starting FastAPI backend..."
cd /app/backend
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1