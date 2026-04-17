"""Celery tasks for flight data ingestion."""
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError, SoftTimeLimitExceeded
import logging
import sys
import os
from typing import Optional

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
    default_retry_delay=300,  # الانتظار 5 دقائق قبل إعادة المحاولة عند الحظر
    time_limit=14400,        # السماح للمهمة بالعمل لمدة 4 ساعات (لأن البيانات التاريخية ضخمة)
    queue="maintenance"      # نضعها في طابور الصيانة كي لا تعطل الجلب اللحظي
)
def ingest_historical_data_task(
    self,
    start_date: str,
    end_date: str,
    region_name: Optional[str] = None
):
    """Celery task to ingest historical flight data in chunks (day by day).

    Args:  
        start_date: Start date in YYYY-MM-DD format  
        end_date: End date in YYYY-MM-DD format  
        region_name: Optional region name filter  
        
    Returns:  
        Dictionary with ingestion statistics  
    """  
    try:  
        logger.info(f"Starting historical data ingestion task: {start_date} to {end_date} (region: {region_name or 'Global'})")  
        
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
            return {  
                "status": "failed",  
                "error": str(exc),  
                "retries_exceeded": True  
            }

@shared_task(queue="default")
def ping_task():
    """Simple ping task for health checks."""
    import time
    return {"status": "pong", "timestamp": time.time()}