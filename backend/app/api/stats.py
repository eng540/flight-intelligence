"""Statistics API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.crud import FlightCRUD, AirlineCRUD
from app.schemas import FlightStatistics, AirlineActivityStats, CountryActivityStats

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/stats", tags=["statistics"])


@router.get("", response_model=FlightStatistics)
async def get_statistics(db: Session = Depends(get_db)):
    """
    Get comprehensive flight statistics.
    
    Returns:
    - Total flights count
    - Daily flight statistics for the last 7 days
    - Top 10 most active airlines
    - Top 10 most active countries
    - Flights today, this week, and this month
    """
    try:
        stats = FlightCRUD.get_statistics(db)
        return FlightStatistics(**stats)
    except Exception as e:
        logger.error(f"Error fetching statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/airlines")
async def get_airline_statistics(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get most active airlines statistics.
    
    Returns a list of airlines ordered by flight count.
    """
    try:
        airlines = AirlineCRUD.get_most_active(db, limit=limit)
        return {"data": airlines}
    except Exception as e:
        logger.error(f"Error fetching airline statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint.
    
    Returns the current status of the API and database connection.
    """
    from datetime import datetime
    from app.schemas import HealthCheck
    
    try:
        # Test database connection
        db.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "disconnected"
    
    return HealthCheck(
        status="healthy" if db_status == "connected" else "unhealthy",
        timestamp=datetime.utcnow(),
        database=db_status
    )
