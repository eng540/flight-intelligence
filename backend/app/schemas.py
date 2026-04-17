"""Pydantic schemas for API request/response validation."""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


class CountryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    iso_code: Optional[str] = Field(None, max_length=3)

class CountryCreate(CountryBase):
    pass

class CountryResponse(CountryBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: Optional[datetime] = None


class AirlineBase(BaseModel):
    icao24: str = Field(..., min_length=4, max_length=6)
    name: Optional[str] = Field(None, max_length=200)
    callsign_prefix: Optional[str] = Field(None, max_length=10)

class AirlineCreate(AirlineBase):
    country_id: Optional[int] = None

class AirlineResponse(AirlineBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    country_id: Optional[int] = None
    country: Optional[CountryResponse] = None
    created_at: Optional[datetime] = None
    flight_count: Optional[int] = 0


class FlightBase(BaseModel):
    icao24: str = Field(..., min_length=4, max_length=6)
    callsign: Optional[str] = Field(None, max_length=20)
    origin_country: Optional[str] = Field(None, max_length=100)

class FlightCreate(FlightBase):
    first_seen: Optional[int] = None
    last_seen: Optional[int] = None
    est_departure_airport: Optional[str] = Field(None, max_length=4)
    est_departure_airport_horiz_distance: Optional[int] = None
    est_departure_airport_vert_distance: Optional[int] = None
    est_arrival_airport: Optional[str] = Field(None, max_length=4)
    est_arrival_airport_horiz_distance: Optional[int] = None
    est_arrival_airport_vert_distance: Optional[int] = None
    est_departure_time: Optional[int] = None
    est_arrival_time: Optional[int] = None
    unique_flight_id: str = Field(..., max_length=100)
    trajectory: Optional[List[Dict[str, Any]]] = None

class FlightResponse(FlightBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    airline_id: Optional[int] = None
    airline: Optional[AirlineResponse] = None
    first_seen: Optional[int] = None
    last_seen: Optional[int] = None
    est_departure_airport: Optional[str] = None
    est_arrival_airport: Optional[str] = None
    est_departure_time: Optional[int] = None
    est_arrival_time: Optional[int] = None
    ingestion_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    duration_minutes: Optional[float] = None
    duration_hours: Optional[float] = None
    trajectory: Optional[List[Dict[str, Any]]] = None


class FlightListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    pages: int
    data: List[FlightResponse]


class FlightFilterParams(BaseModel):
    airline_id: Optional[int] = None
    country: Optional[str] = None
    date_from: Optional[str] = Field(None, description="Date in YYYY-MM-DD format")
    date_to: Optional[str] = Field(None, description="Date in YYYY-MM-DD format")
    departure_airport: Optional[str] = Field(None, max_length=4)
    arrival_airport: Optional[str] = Field(None, max_length=4)
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=500)


# ✅ الجديد: فلتر جغرافي زمني
class FlightGeoFilterParams(BaseModel):
    begin: int = Field(..., description="Start time as Unix timestamp")
    end: int = Field(..., description="End time as Unix timestamp")
    lamin: float = Field(..., description="Minimum latitude")
    lomin: float = Field(..., description="Minimum longitude")
    lamax: float = Field(..., description="Maximum latitude")
    lomax: float = Field(..., description="Maximum longitude")
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=500)


class HistoricalIngestionRequest(BaseModel):
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format")
    end_date: str = Field(..., description="End date in YYYY-MM-DD format")
    region: Optional[str] = Field(None, description="Region name (e.g., middle_east, central_asia, north_africa)")


class TrajectoryPoint(BaseModel):
    time: int
    lat: float
    lon: float
    alt: Optional[float] = None

class TrajectorySchema(BaseModel):
    flight_id: int
    points: List[TrajectoryPoint]


class CountryActivityStats(BaseModel):
    country_name: str
    flight_count: int


class DailyFlightStats(BaseModel):
    date: str
    flight_count: int


class AirlineActivityStats(BaseModel):
    airline_icao24: str
    airline_name: Optional[str]
    flight_count: int


class FlightStatistics(BaseModel):
    total_flights: int
    daily_stats: List[DailyFlightStats]
    top_airlines: List[AirlineActivityStats]
    top_countries: List[CountryActivityStats]
    flights_today: int
    flights_this_week: int
    flights_this_month: int


class HealthCheck(BaseModel):
    status: str
    timestamp: datetime
    database: str
    version: str = "1.0.0"
