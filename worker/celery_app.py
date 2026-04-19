"""Celery application configuration."""
from celery import Celery
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "flight_intelligence",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["worker.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    beat_schedule_filename="/tmp/celerybeat-schedule",
    
    # Beat scheduler
    beat_schedule={
        "realtime-radar-sweep": {
            "task": "worker.tasks.run_realtime_radar_task",
            # 🚀 الحقيقة المطلقة من الكود الأصلي: 300.0 ثانية (5 دقائق)
            "schedule": 300.0,  
        },
    },
    
    task_routes={
        "worker.tasks.run_realtime_radar_task": {"queue": "ingestion"},
        "worker.tasks.run_historical_backfill_task": {"queue": "ingestion"},
    },
)

if __name__ == "__main__":
    celery_app.start()