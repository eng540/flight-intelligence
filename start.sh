#!/bin/bash
set -e

echo "Starting Container Initialization..."

echo "Running database migrations..."
# 🚀 الإصلاح الجذري: إجبار بايثون على تشغيل alembic من البيئة الوهمية الصحيحة
python -m alembic upgrade head

echo "Cleaning up old celery beat schedule files..."
rm -f /tmp/celerybeat-schedule celerybeat-schedule celerybeat-schedule.db celerybeat-schedule.bak celerybeat-schedule.dir

echo "Starting Celery worker..."
celery -A worker.celery_app worker -l info -Q ingestion,maintenance,default &

echo "Starting Celery beat..."
celery -A worker.celery_app beat -l info &

echo "Starting FastAPI backend..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 4