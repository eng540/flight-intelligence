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
    # 🚀 تصحيح التناقض: يجب أن يكون وقت Celery أكبر من وقت HTTP (60s)
    soft_time_limit=120, # 120 ثانية كافية جداً لانتظار HTTP ومعالجة البيانات
    time_limit=150,      # القتل الإجباري
    queue="ingestion"
)
def run_realtime_radar_task(self):
    """مهمة الرادار الحي."""
    logger.info("Starting Realtime Radar Sweep...")
    
    bbox = {
        "lamin": float(os.getenv("BBOX_LAMIN", "12.0")),
        "lomin": float(os.getenv("BBOX_LOMIN", "25.0")),
        "lamax": float(os.getenv("BBOX_LAMAX", "42.0")),
        "lomax": float(os.getenv("BBOX_LOMAX", "60.0"))
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
    soft_time_limit=600, # 10 دقائق للمهام التاريخية
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