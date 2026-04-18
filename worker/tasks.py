"""Celery tasks for flight data ingestion."""
from celery import shared_task
import logging
import os

from worker.engines import RealtimeEngine

logger = logging.getLogger(__name__)

@shared_task(
    bind=True,
    max_retries=0, # لا نعيد المحاولة في الـ Realtime لأن المهمة التالية ستعمل بعد دقيقة
    soft_time_limit=50, # يجب أن تنتهي قبل الدقيقة التالية
    queue="ingestion"
)
def run_realtime_radar_task(self):
    """
    مهمة الرادار الحي: تعمل كل دقيقة لالتقاط حركة الطائرات.
    """
    logger.info("Starting Realtime Radar Sweep...")
    
    # إحداثيات افتراضية (مثال: الشرق الأوسط) يمكن تغييرها من Railway Variables
    bbox = {
        "lamin": float(os.getenv("BBOX_LAMIN", "12.0")),
        "lomin": float(os.getenv("BBOX_LOMIN", "25.0")),
        "lamax": float(os.getenv("BBOX_LAMAX", "42.0")),
        "lomax": float(os.getenv("BBOX_LOMAX", "60.0"))
    }
    
    engine = RealtimeEngine(bbox=bbox)
    engine.run()
    
    return {"status": "completed", "job_id": engine.job.id}