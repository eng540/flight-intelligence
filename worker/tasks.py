"""Celery tasks for flight data ingestion."""
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from worker.engines import RealtimeEngine, HistoricalEngine

logger = logging.getLogger(__name__)

@shared_task(
    bind=True,
    max_retries=0, 
    # 🚀 Increased Celery time limits to accommodate the new 120s HTTP timeout
    soft_time_limit=150, 
    time_limit=180,      
    queue="ingestion"
)
def run_realtime_radar_task(self):
    """مهمة الرادار الحي."""
    logger.info("Starting Realtime Radar Sweep...")
    
    # 🚀 Default Bounding Box set to the Arabian Gulf & Middle East region
    bbox = {
        "lamin": float(os.getenv("BBOX_LAMIN", "12.0")),  # South Yemen/Oman
        "lomin": float(os.getenv("BBOX_LOMIN", "34.0")),  # Red Sea/West Saudi Arabia
        "lamax": float(os.getenv("BBOX_LAMAX", "32.0")),  # North Kuwait/Iraq
        "lomax": float(os.getenv("BBOX_LOMAX", "60.0"))   # Oman/Iran borders
    }
    
    engine = RealtimeEngine(bbox=bbox)
    job_id = engine.job.id
    
    try:
        engine.run()
        return {"status": "completed", "job_id": job_id}
    except SoftTimeLimitExceeded:
        logger.error("Task killed due to SoftTimeLimitExceeded")
        engine._close_job("failed", error="Celery Soft Time Limit Exceeded")
        return {"status": "timeout", "job_id": job_id}


@shared_task(
    bind=True,
    max_retries=1,
    soft_time_limit=600, # 10 minutes for historical tasks
    time_limit=660,
    queue="ingestion"
)
def run_historical_backfill_task(self, start_ts: int, end_ts: int):
    """مهمة جلب البيانات التاريخية."""
    logger.info(f"Starting Historical Backfill from {start_ts} to {end_ts}")
    engine = HistoricalEngine(start_ts=start_ts, end_ts=end_ts)
    job_id = engine.job.id
    
    try:
        engine.run()
        return {"status": "completed", "job_id": job_id}
    except SoftTimeLimitExceeded:
        engine._close_job("failed", error="Timeout")
        return {"status": "timeout", "job_id": job_id}