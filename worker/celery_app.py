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
    
    # Beat scheduler
    beat_schedule={
        "realtime-radar-sweep-every-minute": {
            "task": "worker.tasks.run_realtime_radar_task",
            "schedule": 60.0,  # 60 seconds = Realtime Radar
        },
        # تم إزالة مهمة الحذف (Cleanup) للحفاظ على البيانات التاريخية
    },
    
    task_routes={
        "worker.tasks.run_realtime_radar_task": {"queue": "ingestion"},
    },
)

if __name__ == "__main__":
    celery_app.start()