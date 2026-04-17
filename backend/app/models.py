"""SQLAlchemy models for the Flight Intelligence database."""
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, 
    Boolean, Index, BigInteger, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from datetime import datetime
from typing import Optional


class Country(Base):
    __tablename__ = "countries"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    iso_code = Column(String(3), unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    airlines = relationship("Airline", back_populates="country")


class Airline(Base):
    __tablename__ = "airlines"
    id = Column(Integer, primary_key=True, index=True)
    icao24 = Column(String(6), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=True)
    callsign_prefix = Column(String(10), nullable=True)
    country_id = Column(Integer, ForeignKey("countries.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    country = relationship("Country", back_populates="airlines")
    flights = relationship("Flight", back_populates="airline")
    __table_args__ = (Index('idx_airline_icao24_name', 'icao24', 'name'),)


class Flight(Base):
    __tablename__ = "flights"
    id = Column(Integer, primary_key=True, index=True)
    icao24 = Column(String(6), nullable=False, index=True)
    callsign = Column(String(20), nullable=True, index=True)
    airline_id = Column(Integer, ForeignKey("airlines.id"), nullable=True, index=True)
    origin_country = Column(String(100), nullable=True, index=True)
    first_seen = Column(BigInteger, nullable=True, index=True)
    last_seen = Column(BigInteger, nullable=True, index=True)
    est_departure_airport = Column(String(4), nullable=True, index=True)
    est_departure_airport_horiz_distance = Column(Integer, nullable=True)
    est_departure_airport_vert_distance = Column(Integer, nullable=True)
    est_arrival_airport = Column(String(4), nullable=True, index=True)
    est_arrival_airport_horiz_distance = Column(Integer, nullable=True)
    est_arrival_airport_vert_distance = Column(Integer, nullable=True)
    est_departure_time = Column(BigInteger, nullable=True)
    est_arrival_time = Column(BigInteger, nullable=True)
    trajectory = Column(JSONB, nullable=True)
    ingestion_time = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    unique_flight_id = Column(String(100), unique=True, nullable=False, index=True)
    airline = relationship("Airline", back_populates="flights")
    __table_args__ = (
        Index('idx_flight_time_range', 'first_seen', 'last_seen'),
        Index('idx_flight_airports', 'est_departure_airport', 'est_arrival_airport'),
        Index('idx_flight_ingestion', 'ingestion_time'),
        Index('idx_flight_country', 'origin_country'),
    )

    @property
    def duration_seconds(self) -> Optional[int]:
        if self.first_seen and self.last_seen:
            return self.last_seen - self.first_seen
        return None

    @property
    def duration_minutes(self) -> Optional[float]:
        duration = self.duration_seconds
        if duration:
            return duration / 60
        return None

    @property
    def duration_hours(self) -> Optional[float]:
        duration = self.duration_minutes
        if duration:
            return duration / 60
        return None


class IngestionLog(Base):
    """
    سجل تتبع الاستيعاب — Multi Mode
    يتوافق مع Migration 003 + 004
    المفتاح الفريد المركب: (target_date, region)
    """
    __tablename__ = "ingestion_logs"

    # ─── من Migration 003 ───
    id = Column(Integer, primary_key=True, index=True)
    target_date = Column(String(10), nullable=False, index=True)
    region = Column(String(50), nullable=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    records_fetched = Column(Integer, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(String(500), nullable=True)

    # ─── من Migration 004 ───
    task_id = Column(String(100), nullable=True, index=True)
    start_date = Column(String(20), nullable=True)
    end_date = Column(String(20), nullable=True)

    # ─── القيد الفريد المركب للـ Multi Mode ───
    __table_args__ = (
        UniqueConstraint('target_date', 'region', name='uq_ingestion_target_region'),
        Index('ix_ingestion_logs_target_date', 'target_date'),
        Index('ix_ingestion_logs_task_id', 'task_id'),
    )
