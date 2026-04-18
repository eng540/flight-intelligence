"""SQLAlchemy models for the Flight Intelligence database."""
import enum
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Index, BigInteger, Enum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, deferred
from sqlalchemy.sql import func
from app.database import Base

# ==========================================
# 1. Lookup Tables (البيانات المرجعية)
# ==========================================

class Country(Base):
    """Country lookup table."""
    __tablename__ = "countries"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    iso_code = Column(String(3), unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    airlines = relationship("Airline", back_populates="country")

class Airline(Base):
    """Airline lookup table."""
    __tablename__ = "airlines"
    
    id = Column(Integer, primary_key=True, index=True)
    icao24 = Column(String(6), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=True)
    callsign_prefix = Column(String(10), nullable=True)
    country_id = Column(Integer, ForeignKey("countries.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    country = relationship("Country", back_populates="airlines")
    flights = relationship("Flight", back_populates="airline")
    
    __table_args__ = (Index('idx_airline_icao24_name', 'icao24', 'name'),)

# ==========================================
# 2. Core Data Warehouse (مصدر الحقيقة)
# ==========================================

class Flight(Base):
    """The Source of Truth for all flights."""
    __tablename__ = "flights"
    
    id = Column(Integer, primary_key=True, index=True)
    icao24 = Column(String(6), nullable=False, index=True)
    callsign = Column(String(20), nullable=True, index=True)
    airline_id = Column(Integer, ForeignKey("airlines.id"), nullable=True, index=True)
    origin_country = Column(String(100), nullable=True, index=True)
    
    # Timestamps in Unix Epoch (Seconds) for fast range queries
    first_seen = Column(BigInteger, nullable=False, index=True)
    last_seen = Column(BigInteger, nullable=False, index=True)
    
    est_departure_airport = Column(String(4), nullable=True, index=True)
    est_arrival_airport = Column(String(4), nullable=True, index=True)
    
    # System Metadata
    ingestion_time = Column(DateTime(timezone=True), server_default=func.now())
    unique_flight_id = Column(String(100), unique=True, nullable=False, index=True)
    
    # ⚠️ ARCHITECTURAL DECISION: Deferred JSONB
    # Trajectory is heavy. We defer loading it unless explicitly requested by the API.
    trajectory = deferred(Column(JSONB, nullable=True))
    
    # Relationships
    airline = relationship("Airline", back_populates="flights")
    events = relationship("FlightEvent", back_populates="flight", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_flight_time_range', 'first_seen', 'last_seen'),
        Index('idx_flight_airports', 'est_departure_airport', 'est_arrival_airport'),
    )

# ==========================================
# 3. Intelligence Layer (طبقة الاستخبارات)
# ==========================================

class FlightEvent(Base):
    """Tracks specific events (takeoff, landing, anomaly, deviation)."""
    __tablename__ = "flight_events"
    
    id = Column(Integer, primary_key=True, index=True)
    flight_id = Column(Integer, ForeignKey("flights.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True) 
    timestamp = Column(BigInteger, nullable=False, index=True)
    
    # Flexible payload for the event (e.g., {"lat": 25.0, "lon": 55.0, "severity": "high"})
    data = Column(JSONB, nullable=True)
    
    flight = relationship("Flight", back_populates="events")

# ==========================================
# 4. Operational & Audit Layer (طبقة التشغيل)
# ==========================================

class JobMode(str, enum.Enum):
    HISTORICAL = "historical"
    CONTINUOUS = "continuous"
    REALTIME = "realtime"

class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"

class IngestionJob(Base):
    """Audit log for all ingestion engines."""
    __tablename__ = "ingestion_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(100), nullable=True, index=True) # Celery Task ID
    mode = Column(Enum(JobMode, name="job_mode_enum", create_type=False), nullable=False)
    status = Column(Enum(JobStatus, name="job_status_enum", create_type=False), default=JobStatus.PENDING, nullable=False)
    
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    
    # Engine parameters (e.g., {"bbox": [12.0, 25.0, 42.0, 60.0]})
    params = Column(JSONB, nullable=False)
    
    records_fetched = Column(Integer, default=0)
    error_message = Column(String, nullable=True)