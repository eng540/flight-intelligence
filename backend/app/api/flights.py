"""Flight API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
import logging
import io
import pandas as pd
from datetime import datetime

from app.database import get_db
from app.crud import FlightCRUD
from app.schemas import (
    FlightResponse, FlightListResponse, FlightGeoFilterParams,
    TrajectorySchema, CountryActivityStats, HistoricalIngestionRequest
)
from worker.celery_app import celery_app

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/flights", tags=["flights"])


@router.get("", response_model=FlightListResponse)
async def get_flights(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    skip = (page - 1) * page_size
    flights, total = FlightCRUD.get_all(db, skip=skip, limit=page_size)
    pages = (total + page_size - 1) // page_size
    return FlightListResponse(
        total=total, page=page, page_size=page_size, pages=pages, data=flights
    )


@router.get("/filter", response_model=FlightListResponse)
async def filter_flights(
    airline_id: Optional[int] = Query(None),
    country: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    departure_airport: Optional[str] = Query(None),
    arrival_airport: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    skip = (page - 1) * page_size
    flights, total = FlightCRUD.get_all(
        db, skip=skip, limit=page_size, airline_id=airline_id,
        country=country, date_from=date_from, date_to=date_to,
        departure_airport=departure_airport, arrival_airport=arrival_airport
    )
    pages = (total + page_size - 1) // page_size
    return FlightListResponse(
        total=total, page=page, page_size=page_size, pages=pages, data=flights
    )


# ✅ الجديد: فلتر جغرافي
@router.get("/geo-filter", response_model=FlightListResponse)
async def get_flights_by_geo(
    begin: int = Query(..., description="Start time as Unix timestamp"),
    end: int = Query(..., description="End time as Unix timestamp"),
    lamin: float = Query(..., description="Minimum latitude"),
    lomin: float = Query(..., description="Minimum longitude"),
    lamax: float = Query(..., description="Maximum latitude"),
    lomax: float = Query(..., description="Maximum longitude"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    skip = (page - 1) * page_size
    flights, total = FlightCRUD.get_by_bounding_box(
        db, lamin, lomin, lamax, lomax, begin, end, skip, page_size
    )
    pages = (total + page_size - 1) // page_size
    return FlightListResponse(
        total=total, page=page, page_size=page_size, pages=pages, data=flights
    )


@router.get("/{flight_id}", response_model=FlightResponse)
async def get_flight(flight_id: int, db: Session = Depends(get_db)):
    flight = FlightCRUD.get_by_id(db, flight_id)
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    return flight


@router.get("/{flight_id}/trajectory", response_model=TrajectorySchema)
async def get_flight_trajectory(flight_id: int, db: Session = Depends(get_db)):
    flight = FlightCRUD.get_by_id(db, flight_id)
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    if not flight.trajectory:
        raise HTTPException(status_code=404, detail="Trajectory not found for this flight")
    return {"flight_id": flight_id, "points": flight.trajectory}


# ✅ الجديد: تحليلات الدول
@router.get("/analytics/top-countries", response_model=List[CountryActivityStats])
async def get_top_countries_by_flights(
    begin: int = Query(..., description="Start time as Unix timestamp"),
    end: int = Query(..., description="End time as Unix timestamp"),
    lamin: float = Query(..., description="Minimum latitude"),
    lomin: float = Query(..., description="Minimum longitude"),
    lamax: float = Query(..., description="Maximum latitude"),
    lomax: float = Query(..., description="Maximum longitude"),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    results = FlightCRUD.get_top_countries_in_geo_time(
        db, begin, end, lamin, lomin, lamax, lomax, limit
    )
    return results


@router.post("/ingest-historical", status_code=202)
async def trigger_historical_ingestion(request: HistoricalIngestionRequest):
    """تشغيل محرك الجلب التاريخي في الخلفية."""
    try:
        task = celery_app.send_task(
            'worker.tasks.ingest_historical_data_task',
            args=[request.start_date, request.end_date, request.region]
        )
        return {
            "message": "Historical data ingestion started successfully in the background.",
            "task_id": task.id,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "region": request.region or "Global"
        }
    except Exception as e:
        logger.error(f"Failed to trigger historical ingestion: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start ingestion task: {str(e)}")
