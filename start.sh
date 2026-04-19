#!/bin/bash
set -e

echo "Starting Container Initialization..."

# 1. الحقيقة: ملف alembic.ini موجود في مجلد backend
# يجب الدخول إليه لتشغيل الترحيلات بنجاح كما هو محدد في الـ Makefile الخاص بك
echo "Running database migrations..."
cd backend
alembic upgrade head
cd ..

# 2. الحقيقة: مسح ملفات المجدول التالفة لمنع تجمد Celery Beat
echo "Cleaning up old celery beat schedule files..."
rm -f /tmp/celerybeat-schedule celerybeat-schedule celerybeat-schedule.db celerybeat-schedule.bak celerybeat-schedule.dir

# 3. الحقيقة: تشغيل الخدمات بناءً على إعدادات PYTHONPATH الحالية
echo "Starting Celery worker..."
celery -A worker.celery_app worker -l info -Q ingestion,maintenance,default &

echo "Starting Celery beat..."
celery -A worker.celery_app beat -l info &

echo "Starting FastAPI backend..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 4