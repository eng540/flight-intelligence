"""Celery tasks for flight data ingestion."""
from celery import shared_task
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
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
    
    # 🚀 الإصلاح الجذري: حفظ الـ ID قبل تشغيل المحرك
    # لأن engine.run() تقوم بإغلاق جلسة قاعدة البيانات (db.close())
    # ومحاولة قراءة engine.job.id بعدها ستؤدي إلى DetachedInstanceError
    job_id = engine.job.id
    
    engine.run()
    
    # استخدام المتغير المحفوظ بدلاً من قراءته من الكائن المغلق
    return {"status": "completed", "job_id": job_id}