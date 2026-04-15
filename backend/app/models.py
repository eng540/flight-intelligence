"""SQLAlchemy models for the Flight Intelligence database."""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Index, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from datetime import datetime
from typing import Optional


class Country(Base):
    """Country model for airline origin countries."""
    __tablename__ = "countries"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    iso_code = Column(String(3), unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    airlines = relationship("Airline", back_populates="country")
    
    def __repr__(self):
        return f"<Country(name='{self.name}')>"


class Airline(Base):
    """Airline model containing airline information."""
    __tablename__ = "airlines"
    
    id = Column(Integer, primary_key=True, index=True)
    icao24 = Column(String(6), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=True)
    callsign_prefix = Column(String(10), nullable=True)
    country_id = Column(Integer, ForeignKey("countries.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    country = relationship("Country", back_populates="airlines")
    flights = relationship("Flight", back_populates="airline")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_airline_icao24_name', 'icao24', 'name'),
    )
    
    def __repr__(self):
        return f"<Airline(icao24='{self.icao24}', name='{self.name}')>"


class Flight(Base):
    """Flight model containing flight tracking information."""
    __tablename__ = "flights"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Aircraft identification
    icao24 = Column(String(6), nullable=False, index=True)
    callsign = Column(String(20), nullable=True, index=True)
    
    # Airline relationship
    airline_id = Column(Integer, ForeignKey("airlines.id"), nullable=True, index=True)
    
    # Origin country
    origin_country = Column(String(100), nullable=True, index=True)
    
    # Timestamps (Unix epoch in seconds)
    first_seen = Column(BigInteger, nullable=True, index=True)
    last_seen = Column(BigInteger, nullable=True, index=True)
    
    # Departure airport
    est_departure_airport = Column(String(4), nullable=True, index=True)
    est_departure_airport_horiz_distance = Column(Integer, nullable=True)
    est_departure_airport_vert_distance = Column(Integer, nullable=True)
    
    # Arrival airport
    est_arrival_airport = Column(String(4), nullable=True, index=True)
    est_arrival_airport_horiz_distance = Column(Integer, nullable=True)
    est_arrival_airport_vert_distance = Column(Integer, nullable=True)
    
    # Departure time
    est_departure_time = Column(BigInteger, nullable=True)
    est_arrival_time = Column(BigInteger, nullable=True)
    
    # System tracking
    ingestion_time = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Unique identifier to prevent duplicates
    unique_flight_id = Column(String(100), unique=True, nullable=False, index=True)
    
    # Relationships
    airline = relationship("Airline", back_populates="flights")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_flight_time_range', 'first_seen', 'last_seen'),
        Index('idx_flight_airports', 'est_departure_airport', 'est_arrival_airport'),
        Index('idx_flight_ingestion', 'ingestion_time'),
        Index('idx_flight_country', 'origin_country'),
    )
    
    def __repr__(self):
        return f"<Flight(icao24='{self.icao24}', callsign='{self.callsign}')>"
    
    @property
    def duration_seconds(self) -> Optional[int]:
        """Calculate flight duration in seconds."""
        if self.first_seen and self.last_seen:
            return self.last_seen - self.first_seen
        return None
    
    @property
    def duration_minutes(self) -> Optional[float]:
        """Calculate flight duration in minutes."""
        duration = self.duration_seconds
        if duration:
            return duration / 60
        return None
    
    @property
    def duration_hours(self) -> Optional[float]:
        """Calculate flight duration in hours."""
        duration = self.duration_minutes
        if duration:
            return duration / 60
        return None
