"""Statistics API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text  # 🚀 تم إضافة هذا الاستيراد لإصلاح خطأ فحص الصحة
from typing import Optional, List, Dict, Any
import logging

from app.database import get_db
from app.crud import FlightCRUD, AirlineCRUD
from app.schemas import FlightStatistics, HealthCheck

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/stats", tags=["statistics"])

@router.get("", response_model=FlightStatistics)
async def get_statistics(db: Session = Depends(get_db)):
    """Get comprehensive flight statistics."""
    try:
        stats = FlightCRUD.get_statistics(db)
        return FlightStatistics(**stats)
    except Exception as e:
        logger.error(f"Error fetching statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ==========================================
# 🚀 Custom Analytics Endpoints
# ==========================================

@router.get("/top-countries", response_model=List[Dict[str, Any]])
async def get_top_countries_by_flights(
    begin: Optional[int] = Query(None, description="Start time as Unix timestamp"),
    end: Optional[int] = Query(None, description="End time as Unix timestamp"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    نقطة نهاية للتحليلات المخصصة: أكثر دول بها حركة طيران ضمن نطاق زمني محدد.
    """
    try:
        from sqlalchemy import func, desc
        from app.models import Flight
        
        query = db.query(
            Flight.origin_country,
            func.count(Flight.id).label('flight_count')
        )
        
        if begin:
            query = query.filter(Flight.first_seen >= begin)
        if end:
            query = query.filter(Flight.last_seen <= end)
            
        results = query.group_by(Flight.origin_country)\
                       .order_by(desc('flight_count'))\
                       .limit(limit).all()
                       
        return [{"country": r.origin_country or "Unknown", "count": r.flight_count} for r in results]
    except Exception as e:
        logger.error(f"Error fetching top countries: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/airlines")
async def get_airline_statistics(limit: int = 10, db: Session = Depends(get_db)):
    """Get most active airlines statistics."""
    try:
        airlines = AirlineCRUD.get_most_active(db, limit=limit)
        return {"data": airlines}
    except Exception as e:
        logger.error(f"Error fetching airline statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/health", response_model=HealthCheck)
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint."""
    from datetime import datetime
    try:
        # 🚀 الإصلاح الجذري: تغليف الاستعلام بدالة text()
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "disconnected"
    
    return HealthCheck(
        status="healthy" if db_status == "connected" else "unhealthy",
        timestamp=datetime.utcnow(),
        database=db_status
    )