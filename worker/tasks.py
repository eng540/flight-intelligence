"""Celery tasks for flight data ingestion."""
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError, SoftTimeLimitExceeded
import logging
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from worker.ingestion_service import FlightIngestionService

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=300,  # 5 minutes
    time_limit=600,  # 10 minutes
    queue="ingestion"
)
def ingest_flights_task(self, hours: int = 2):
    """Celery task to ingest flight data.
    
    Args:
        hours: Number of hours to look back for flights
        
    Returns:
        Dictionary with ingestion statistics
    """
    try:
        logger.info(f"Starting flight ingestion task for last {hours} hours")
        
        with FlightIngestionService() as service:
            stats = service.ingest_recent_flights(hours)
            
        logger.info(f"Flight ingestion completed: {stats}")
        return {
            "status": "success",
            "stats": stats,
            "hours": hours
        }
        
    except SoftTimeLimitExceeded:
        logger.error("Flight ingestion task timed out")
        # Don't retry on timeout
        return {
            "status": "timeout",
            "error": "Task exceeded time limit"
        }
        
    except Exception as exc:
        logger.error(f"Flight ingestion task failed: {exc}", exc_info=True)
        
        # Retry on failure
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for flight ingestion task")
            return {
                "status": "failed",
                "error": str(exc),
                "retries_exceeded": True
            }


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    soft_time_limit=600,  # 10 minutes
    time_limit=1200,  # 20 minutes
    queue="maintenance"
)
def cleanup_old_data_task(self, days: int = 30):
    """Celery task to clean up old flight data.
    
    Args:
        days: Number of days to keep (delete older data)
        
    Returns:
        Dictionary with cleanup statistics
    """
    try:
        logger.info(f"Starting cleanup task for data older than {days} days")
        
        with FlightIngestionService() as service:
            deleted = service.cleanup_old_data(days)
            
        logger.info(f"Cleanup completed: {deleted} records deleted")
        return {
            "status": "success",
            "deleted": deleted,
            "days": days
        }
        
    except SoftTimeLimitExceeded:
        logger.error("Cleanup task timed out")
        return {
            "status": "timeout",
            "error": "Task exceeded time limit"
        }
        
    except Exception as exc:
        logger.error(f"Cleanup task failed: {exc}", exc_info=True)
        
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for cleanup task")
            return {
                "status": "failed",
                "error": str(exc),
                "retries_exceeded": True
            }


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    queue="ingestion"
)
def ingest_historical_data_task(
    self,
    begin_timestamp: int,
    end_timestamp: int
):
    """Celery task to ingest historical flight data.
    
    Args:
        begin_timestamp: Start time as Unix timestamp
        end_timestamp: End time as Unix timestamp
        
    Returns:
        Dictionary with ingestion statistics
    """
    try:
        logger.info(f"Starting historical data ingestion: {begin_timestamp} to {end_timestamp}")
        
        with FlightIngestionService() as service:
            stats = service.ingest_flights_by_time_range(begin_timestamp, end_timestamp)
            
        logger.info(f"Historical ingestion completed: {stats}")
        return {
            "status": "success",
            "stats": stats,
            "begin": begin_timestamp,
            "end": end_timestamp
        }
        
    except Exception as exc:
        logger.error(f"Historical ingestion task failed: {exc}", exc_info=True)
        
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            return {
                "status": "failed",
                "error": str(exc),
                "retries_exceeded": True
            }


@shared_task(queue="default")
def ping_task():
    """Simple ping task for health checks."""
    return {"status": "pong", "timestamp": __import__('time').time()}
