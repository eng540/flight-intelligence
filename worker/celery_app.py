"""Celery application configuration."""
from celery import Celery
from celery.signals import task_failure, task_success
import os
import logging

logger = logging.getLogger(__name__)

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
    task_always_eager=False,
    task_store_eager_result=False,
    task_ignore_result=False,
    task_track_started=True,
    result_expires=3600,
    result_backend=REDIS_URL,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    
    # ✅ إصلاح التحذير
    broker_connection_retry_on_startup=True,
    
    # ✅ إزالة cleanup من الجدولة الدورية
    beat_schedule={
        "ingest-flights-every-5-minutes": {
            "task": "worker.tasks.ingest_flights_task",
            "schedule": 300.0,
            "args": (2,),
        },
        # "cleanup-old-data-daily": REMOVED
    },
    
    beat_schedule_filename="/tmp/celerybeat-schedule",
    
    task_routes={
        "worker.tasks.ingest_flights_task": {"queue": "ingestion"},
        "worker.tasks.cleanup_old_data_task": {"queue": "maintenance"},
        "worker.tasks.ingest_historical_data_task": {"queue": "maintenance"},
    },
)

@task_success.connect
def handle_task_success(sender=None, result=None, **kwargs):
    logger.info(f"Task {sender.name} completed successfully: {result}")

@task_failure.connect
def handle_task_failure(sender=None, task_id=None, exception=None, **kwargs):
    logger.error(f"Task {sender.name} failed: {exception}")

@celery_app.task(bind=True, max_retries=3)
def health_check_task(self):
    return {"status": "healthy", "worker": self.request.hostname}

if __name__ == "__main__":
    celery_app.start()
