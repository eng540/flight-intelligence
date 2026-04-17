"""Statistics API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

from app.database import get_db
from app.crud import FlightCRUD

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/stats", tags=["statistics"])


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """System health check including database connectivity."""
    try:
        # ✅ إصلاح: استخدام text() لـ SQLAlchemy 2.0
        db.execute(text('SELECT 1'))
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }


@router.get("")
async def get_stats(db: Session = Depends(get_db)):
    """Get comprehensive flight statistics."""
    try:
        stats = FlightCRUD.get_statistics(db)
        return stats
    except Exception as e:
        logger.error(f"Error fetching statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch statistics")


@router.get("/airlines")
async def get_airline_stats(limit: int = 10, db: Session = Depends(get_db)):
    """Get most active airlines."""
    try:
        airlines = FlightCRUD.get_most_active_airlines(db, limit)
        return {"airlines": airlines}
    except Exception as e:
        logger.error(f"Error fetching airline stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch airline statistics")


from datetime import datetime
