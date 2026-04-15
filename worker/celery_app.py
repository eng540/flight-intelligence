"""Celery application configuration."""
from celery import Celery
from celery.signals import task_failure, task_success
import os
import logging

logger = logging.getLogger(__name__)

# Get Redis URL from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
celery_app = Celery(
    "flight_intelligence",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["worker.tasks"]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution
    task_always_eager=False,
    task_store_eager_result=False,
    task_ignore_result=False,
    task_track_started=True,
    
    # Result backend
    result_expires=3600,  # Results expire after 1 hour
    result_backend=REDIS_URL,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    
    # Beat scheduler
    beat_schedule={
        "ingest-flights-every-5-minutes": {
            "task": "worker.tasks.ingest_flights_task",
            "schedule": 300.0,  # 5 minutes in seconds
            "args": (2,),  # Look back 2 hours
        },
        "cleanup-old-data-daily": {
            "task": "worker.tasks.cleanup_old_data_task",
            "schedule": 86400.0,  # 24 hours in seconds
            "args": (30,),  # Keep 30 days
        },
    },
    
    # Beat scheduler filename (for file-based scheduler)
    beat_schedule_filename="/tmp/celerybeat-schedule",
    
    # Task routes
    task_routes={
        "worker.tasks.ingest_flights_task": {"queue": "ingestion"},
        "worker.tasks.cleanup_old_data_task": {"queue": "maintenance"},
    },
)


@task_success.connect
def handle_task_success(sender=None, result=None, **kwargs):
    """Handle successful task completion."""
    logger.info(f"Task {sender.name} completed successfully: {result}")


@task_failure.connect
def handle_task_failure(sender=None, task_id=None, exception=None, **kwargs):
    """Handle task failure."""
    logger.error(f"Task {sender.name} failed: {exception}")


# Health check task
@celery_app.task(bind=True, max_retries=3)
def health_check_task(self):
    """Health check task."""
    return {"status": "healthy", "worker": self.request.hostname}


if __name__ == "__main__":
    celery_app.start()
