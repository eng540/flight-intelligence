"""Flight data ingestion service."""
import logging
import sys
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from worker.opensky_client import OpenSkyClient
from worker.data_processor import FlightDataProcessor
from app.database import SessionLocal
from app.crud import FlightCRUD, AirlineCRUD, CountryCRUD
from app.schemas import FlightCreate

logger = logging.getLogger(__name__)


class FlightIngestionService:
    """Service for ingesting flight data from OpenSky API."""
    
    def __init__(self):
        """Initialize the ingestion service."""
        self.client = OpenSkyClient()
        self.processor = FlightDataProcessor()
        self.db = None
    
    def __enter__(self):
        """Context manager entry."""
        self.db = SessionLocal()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.db:
            self.db.close()
    
    def ingest_recent_flights(self, hours: int = 2) -> Dict[str, int]:
        """Ingest flights from recent hours.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dictionary with ingestion statistics
        """
        logger.info(f"Starting ingestion for last {hours} hours")
        
        try:
            # Fetch flights from OpenSky
            flights_data = self.client.get_recent_flights(hours)
            
            if not flights_data:
                logger.info("No flights found")
                return {"created": 0, "updated": 0, "skipped": 0}
            
            logger.info(f"Fetched {len(flights_data)} flights from OpenSky")
            
            # Process and clean data
            processed_flights = self.processor.process_flights(flights_data)
            
            if not processed_flights:
                logger.info("No valid flights after processing")
                return {"created": 0, "updated": 0, "skipped": 0}
            
            # Remove duplicates
            unique_flights = self.processor.remove_duplicates(processed_flights)
            
            # Ingest flights into database
            stats = self._ingest_flights(unique_flights)
            
            logger.info(f"Ingestion complete: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error during ingestion: {e}", exc_info=True)
            return {"created": 0, "updated": 0, "skipped": 0, "error": str(e)}
    
    def ingest_flights_by_time_range(
        self,
        begin: int,
        end: int
    ) -> Dict[str, int]:
        """Ingest flights for a specific time range.
        
        Args:
            begin: Start time as Unix timestamp
            end: End time as Unix timestamp
            
        Returns:
            Dictionary with ingestion statistics
        """
        logger.info(f"Starting ingestion for time range: {begin} to {end}")
        
        try:
            # Fetch flights from OpenSky
            flights_data = self.client.get_all_flights(begin, end)
            
            if not flights_data:
                logger.info("No flights found")
                return {"created": 0, "updated": 0, "skipped": 0}
            
            logger.info(f"Fetched {len(flights_data)} flights from OpenSky")
            
            # Process and clean data
            processed_flights = self.processor.process_flights(flights_data)
            
            if not processed_flights:
                logger.info("No valid flights after processing")
                return {"created": 0, "updated": 0, "skipped": 0}
            
            # Remove duplicates
            unique_flights = self.processor.remove_duplicates(processed_flights)
            
            # Ingest flights into database
            stats = self._ingest_flights(unique_flights)
            
            logger.info(f"Ingestion complete: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error during ingestion: {e}", exc_info=True)
            return {"created": 0, "updated": 0, "skipped": 0, "error": str(e)}
    
    def _ingest_flights(self, flights: List[Dict[str, Any]]) -> Dict[str, int]:
        """Ingest processed flights into database.
        
        Args:
            flights: List of processed flight data
            
        Returns:
            Dictionary with ingestion statistics
        """
        created = 0
        updated = 0
        skipped = 0
        
        for flight_data in flights:
            try:
                # Create or get airline
                airline_info = self.processor.extract_airline_info(flight_data)
                if airline_info:
                    airline = AirlineCRUD.get_or_create(
                        self.db,
                        icao24=airline_info["icao24"],
                        country_name=airline_info.get("country_name")
                    )
                    flight_data["airline_id"] = airline.id
                
                # Create flight schema
                flight_create = FlightCreate(**flight_data)
                
                # Check if flight exists
                existing = FlightCRUD.get_by_unique_id(
                    self.db, 
                    flight_data["unique_flight_id"]
                )
                
                if existing:
                    # Update existing flight
                    update_data = flight_create.model_dump(exclude={'unique_flight_id'})
                    for key, value in update_data.items():
                        setattr(existing, key, value)
                    updated += 1
                else:
                    # Create new flight
                    flight = FlightCRUD.create_or_update(self.db, flight_create)
                    if flight:
                        created += 1
                    else:
                        skipped += 1
                
                # Commit every 50 records
                if (created + updated) % 50 == 0:
                    self.db.commit()
                    logger.debug(f"Committed batch: {created} created, {updated} updated")
                    
            except Exception as e:
                logger.error(f"Error ingesting flight {flight_data.get('unique_flight_id')}: {e}")
                skipped += 1
                continue
        
        # Final commit
        self.db.commit()
        
        return {"created": created, "updated": updated, "skipped": skipped}
    
    def cleanup_old_data(self, days: int = 30) -> int:
        """Remove flight data older than specified days.
        
        Args:
            days: Number of days to keep
            
        Returns:
            Number of records deleted
        """
        logger.info(f"Cleaning up flights older than {days} days")
        deleted = FlightCRUD.delete_old_flights(self.db, days)
        logger.info(f"Deleted {deleted} old flight records")
        return deleted


def run_ingestion(hours: int = 2) -> Dict[str, int]:
    """Run flight ingestion (entry point for scheduler).
    
    Args:
        hours: Number of hours to look back
        
    Returns:
        Dictionary with ingestion statistics
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    with FlightIngestionService() as service:
        stats = service.ingest_recent_flights(hours)
        return stats


if __name__ == "__main__":
    # Run ingestion when called directly
    stats = run_ingestion(hours=2)
    print(f"Ingestion stats: {stats}")
