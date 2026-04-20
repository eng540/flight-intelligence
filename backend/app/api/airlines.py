"""Airline API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.crud import AirlineCRUD
from app.schemas import AirlineResponse, AirlineCreate
from typing import List

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/airlines", tags=["airlines"])

@router.get("", response_model=List[AirlineResponse])
async def get_airlines(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    db: Session = Depends(get_db)
):
    """Get all airlines with pagination."""
    try:
        airlines = AirlineCRUD.get_all(db, skip=skip, limit=limit)
        return airlines
    except Exception as e:
        logger.error(f"Error fetching airlines: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{airline_id}", response_model=AirlineResponse)
async def get_airline(airline_id: int, db: Session = Depends(get_db)):
    """Get a specific airline by ID."""
    airline = AirlineCRUD.get_by_id(db, airline_id)
    if not airline:
        raise HTTPException(status_code=404, detail="Airline not found")
    return airline