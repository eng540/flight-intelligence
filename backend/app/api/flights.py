"""Flight API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
import logging
import io
import pandas as pd
from datetime import datetime
from celery import Celery
import os

from app.database import get_db
from app.crud import FlightCRUD
from app.schemas import (
    FlightResponse, FlightListResponse, FlightGeoFilterParams,
    TrajectorySchema, CountryActivityStats, HistoricalIngestionRequest
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/flights", tags=["flights"])

# ─── تكوين Celery App صراحةً للـ Backend ───
celery_app = Celery('flight_intelligence')
celery_app.conf.update(
    broker_url=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    result_backend=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
)

@router.get("", response_model=FlightListResponse)
async def get_flights(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
    db: Session = Depends(get_db)
):
    """Get all flights with pagination."""
    try:
        skip = (page - 1) * page_size
        flights, total = FlightCRUD.get_all(db, skip=skip, limit=page_size)
        pages = (total + page_size - 1) // page_size

        return FlightListResponse(
            total=total, page=page, page_size=page_size, pages=pages, data=flights
        )
    except Exception as e:
        logger.error(f"Error fetching flights: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/filter", response_model=FlightListResponse)
async def filter_flights(
    airline_id: Optional[int] = Query(None, description="Filter by airline ID"),
    country: Optional[str] = Query(None, description="Filter by origin country"),
    date_from: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    departure_airport: Optional[str] = Query(None, description="Filter by departure airport ICAO code"),
    arrival_airport: Optional[str] = Query(None, description="Filter by arrival airport ICAO code"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
    db: Session = Depends(get_db)
):
    """Filter flights by various criteria."""
    try:
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
    except Exception as e:
        logger.error(f"Error filtering flights: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/geo-filter", response_model=FlightListResponse)
async def get_flights_by_geo(
    begin: int = Query(..., description="Start time as Unix timestamp"),
    end: int = Query(..., description="End time as Unix timestamp"),
    lamin: float = Query(..., description="Minimum latitude"),
    lomin: float = Query(..., description="Minimum longitude"),
    lamax: float = Query(..., description="Maximum latitude"),
    lomax: float = Query(..., description="Maximum longitude"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
    db: Session = Depends(get_db)
):
    """Get flights within a specific geographical area and time interval."""
    try:
        skip = (page - 1) * page_size
        flights, total = FlightCRUD.get_by_bounding_box(
            db, lamin, lomin, lamax, lomax, begin, end, skip, page_size
        )
        pages = (total + page_size - 1) // page_size
        return FlightListResponse(
            total=total, page=page, page_size=page_size, pages=pages, data=flights
        )
    except Exception as e:
        logger.error(f"Error fetching geo-filtered flights: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{flight_id}", response_model=FlightResponse)
async def get_flight(flight_id: int, db: Session = Depends(get_db)):
    """Get a specific flight by ID."""
    flight = FlightCRUD.get_by_id(db, flight_id)
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    return flight


@router.get("/{flight_id}/trajectory", response_model=TrajectorySchema)
async def get_flight_trajectory(flight_id: int, db: Session = Depends(get_db)):
    """Get trajectory data for a specific flight."""
    flight = FlightCRUD.get_by_id(db, flight_id)
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    if not flight.trajectory:
        raise HTTPException(status_code=404, detail="Trajectory not found for this flight")
    return {"flight_id": flight_id, "points": flight.trajectory}


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
    """Get top countries by flight count within a geo/time bounding box."""
    try:
        results = FlightCRUD.get_top_countries_in_geo_time(
            db, begin, end, lamin, lomin, lamax, lomax, limit
        )
        return results
    except Exception as e:
        logger.error(f"Error fetching top countries analytics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/export/excel")
async def export_flights_excel(
    airline_id: Optional[int] = Query(None, description="Filter by airline ID"),
    country: Optional[str] = Query(None, description="Filter by origin country"),
    date_from: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    departure_airport: Optional[str] = Query(None, description="Filter by departure airport ICAO code"),
    arrival_airport: Optional[str] = Query(None, description="Filter by arrival airport ICAO code"),
    limit: int = Query(10000, ge=1, le=50000, description="Maximum number of records to export"),
    db: Session = Depends(get_db)
):
    """Export flights to Excel file."""
    try:
        flights, total = FlightCRUD.get_all(
            db, skip=0, limit=limit, airline_id=airline_id, country=country,
            date_from=date_from, date_to=date_to,
            departure_airport=departure_airport, arrival_airport=arrival_airport
        )

        if not flights:
            raise HTTPException(status_code=404, detail="No flights found for export")

        data = []
        for flight in flights:
            data.append({
                "ID": flight.id,
                "ICAO24": flight.icao24,
                "Callsign": flight.callsign,
                "Airline": flight.airline.name if flight.airline else "Unknown",
                "Origin Country": flight.origin_country,
                "First Seen": datetime.fromtimestamp(flight.first_seen).strftime("%Y-%m-%d %H:%M:%S") if flight.first_seen else "",
                "Last Seen": datetime.fromtimestamp(flight.last_seen).strftime("%Y-%m-%d %H:%M:%S") if flight.last_seen else "",
                "Departure Airport": flight.est_departure_airport,
                "Arrival Airport": flight.est_arrival_airport,
                "Duration (hours)": round(flight.duration_hours, 2) if flight.duration_hours else "",
            })

        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Flights')
            worksheet = writer.sheets['Flights']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width

        output.seek(0)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"flights_export_{timestamp}.xlsx"

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting flights: {e}")
        raise HTTPException(status_code=500, detail="Error generating export file")


@router.post("/ingest-historical", status_code=202)
async def trigger_historical_ingestion(request: HistoricalIngestionRequest):
    """
    تشغيل محرك جلب البيانات التاريخية في الخلفية (Background Task).
    يستخدم send_task بدلاً من استيراد المهمة مباشرةً لتجنب مشاكل الاتصال.
    """
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
