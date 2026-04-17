"""Pydantic schemas for API request/response validation."""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

# ============== Country Schemas ==============

class CountryBase(BaseModel):
    """Base country schema."""
    name: str = Field(..., min_length=1, max_length=100)
    iso_code: Optional[str] = Field(None, max_length=3)

class CountryCreate(CountryBase):
    """Schema for creating a country."""
    pass

class CountryResponse(CountryBase):
    """Schema for country response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int  
    created_at: Optional[datetime] = None

# ============== Airline Schemas ==============

class AirlineBase(BaseModel):
    """Base airline schema."""
    icao24: str = Field(..., min_length=4, max_length=6)
    name: Optional[str] = Field(None, max_length=200)
    callsign_prefix: Optional[str] = Field(None, max_length=10)

class AirlineCreate(AirlineBase):
    """Schema for creating an airline."""
    country_id: Optional[int] = None

class AirlineResponse(AirlineBase):
    """Schema for airline response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int  
    country_id: Optional[int] = None  
    country: Optional[CountryResponse] = None  
    created_at: Optional[datetime] = None  
    flight_count: Optional[int] = 0

# ============== Flight Schemas ==============

class FlightBase(BaseModel):
    """Base flight schema."""
    icao24: str = Field(..., min_length=4, max_length=6)
    callsign: Optional[str] = Field(None, max_length=20)
    origin_country: Optional[str] = Field(None, max_length=100)

class FlightCreate(FlightBase):
    """Schema for creating a flight."""
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
    trajectory: Optional[List[Dict[str, Any]]] = None  # <-- الحقل الجديد

class FlightResponse(FlightBase):
    """Schema for flight response."""
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
    trajectory: Optional[List[Dict[str, Any]]] = None  # <-- الحقل الجديد

class FlightListResponse(BaseModel):
    """Schema for paginated flight list response."""
    total: int
    page: int
    page_size: int
    pages: int
    data: List[FlightResponse]

# ============== Filter Schemas ==============

class FlightFilterParams(BaseModel):
    """Schema for flight filter parameters."""
    airline_id: Optional[int] = None
    country: Optional[str] = None
    date_from: Optional[str] = Field(None, description="Date in YYYY-MM-DD format")
    date_to: Optional[str] = Field(None, description="Date in YYYY-MM-DD format")
    departure_airport: Optional[str] = Field(None, max_length=4)
    arrival_airport: Optional[str] = Field(None, max_length=4)
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=500)

class HistoricalIngestionRequest(BaseModel):
    """Schema for requesting historical data ingestion."""
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format (e.g., 2026-02-15)")
    end_date: str = Field(..., description="End date in YYYY-MM-DD format (e.g., 2026-04-08)")
    region: Optional[str] = Field(None, description="Region name (e.g., middle_east, central_asia, north_africa)")

# ============== Statistics Schemas ==============

class DailyFlightStats(BaseModel):
    """Schema for daily flight statistics."""
    date: str
    flight_count: int

class AirlineActivityStats(BaseModel):
    """Schema for airline activity statistics."""
    airline_icao24: str
    airline_name: Optional[str]
    flight_count: int

class CountryActivityStats(BaseModel):
    """Schema for country activity statistics."""
    country_name: str
    flight_count: int

class FlightStatistics(BaseModel):
    """Schema for comprehensive flight statistics."""
    total_flights: int
    daily_stats: List[DailyFlightStats]
    top_airlines: List[AirlineActivityStats]
    top_countries: List[CountryActivityStats]
    flights_today: int
    flights_this_week: int
    flights_this_month: int

# ============== Health Check Schema ==============

class HealthCheck(BaseModel):
    """Schema for health check response."""
    status: str
    timestamp: datetime
    database: str
    version: str = "1.0.0"