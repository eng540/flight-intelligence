"""Statistics API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging
from datetime import datetime

from app.database import get_db
from app.crud import FlightCRUD

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/stats", tags=["statistics"])


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """System health check including database connectivity."""
    try:
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
