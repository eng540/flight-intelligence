"""Celery tasks for flight data ingestion."""
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError, SoftTimeLimitExceeded
import logging
import sys
import os
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from worker.ingestion_service import FlightIngestionService

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=300,
    time_limit=600,
    queue="ingestion",
    name="worker.tasks.ingest_flights_task"  # ✅ اسم显式 للتأكد من التسجيل
)
def ingest_flights_task(self, hours: int = 2, region: Optional[str] = None):
    """Celery task to ingest recent flight data."""
    try:
        logger.info(f"Starting flight ingestion task for last {hours} hours (region: {region or 'global'})")

        with FlightIngestionService() as service:
            stats = service.ingest_recent_flights(hours, region=region)

        logger.info(f"Flight ingestion completed: {stats}")
        return {
            "status": "success",
            "stats": stats,
            "hours": hours,
            "region": region
        }

    except SoftTimeLimitExceeded:
        logger.error("Flight ingestion task timed out")
        return {"status": "timeout", "error": "Task exceeded time limit"}

    except Exception as exc:
        logger.error(f"Flight ingestion task failed: {exc}", exc_info=True)
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for flight ingestion task")
            return {"status": "failed", "error": str(exc), "retries_exceeded": True}


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    soft_time_limit=600,
    time_limit=1200,
    queue="maintenance",
    name="worker.tasks.cleanup_old_data_task"
)
def cleanup_old_data_task(self, days: int = 30):
    """Celery task to clean up old flight data (protected for historical data)."""
    try:
        logger.info(f"Starting cleanup task for data older than {days} days")

        with FlightIngestionService() as service:
            deleted = service.cleanup_old_data(days)

        logger.info(f"Cleanup completed: {deleted} records deleted")
        return {"status": "success", "deleted": deleted, "days": days}

    except SoftTimeLimitExceeded:
        logger.error("Cleanup task timed out")
        return {"status": "timeout", "error": "Task exceeded time limit"}

    except Exception as exc:
        logger.error(f"Cleanup task failed: {exc}", exc_info=True)
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            return {"status": "failed", "error": str(exc), "retries_exceeded": True}


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    time_limit=14400,
    queue="maintenance",
    name="worker.tasks.ingest_historical_data_task"
)
def ingest_historical_data_task(self, start_date: str, end_date: str, region_name: Optional[str] = None):
    """Celery task to ingest historical flight data day by day."""
    try:
        logger.info(f"Starting historical ingestion: {start_date} to {end_date} (region: {region_name or 'Global'})")

        with FlightIngestionService() as service:
            stats = service.ingest_historical_data_chunked(start_date, end_date, region_name)

        logger.info(f"Historical ingestion task completed: {stats}")
        return {
            "status": "success",
            "stats": stats,
            "start_date": start_date,
            "end_date": end_date,
            "region": region_name
        }

    except Exception as exc:
        logger.error(f"Historical ingestion task failed: {exc}", exc_info=True)
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            return {"status": "failed", "error": str(exc), "retries_exceeded": True}


@shared_task(queue="default", name="worker.tasks.ping_task")
def ping_task():
    """Simple ping task for health checks."""
    import time
    return {"status": "pong", "timestamp": time.time()}
