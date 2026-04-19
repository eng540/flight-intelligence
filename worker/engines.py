"""Ingestion Engines for Flight Intelligence."""
import logging
import time
import hashlib
from datetime import datetime
from typing import Dict, Any
from sqlalchemy.orm.attributes import flag_modified

from app.database import SessionLocal
from app.models import IngestionJob, JobMode, JobStatus, Flight, FlightEvent, Airline
from worker.opensky_client import OpenSkyClient

logger = logging.getLogger(__name__)

class BaseEngine:
    def __init__(self, mode: JobMode, params: Dict[str, Any]):
        self.mode = mode
        self.params = params
        self.db = SessionLocal()
        self.client = OpenSkyClient()
        self.job = self._create_job()

    def _create_job(self) -> IngestionJob:
        job = IngestionJob(mode=self.mode, status=JobStatus.RUNNING, params=self.params)
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def _close_job(self, status: str, records: int = 0, error: str = None):
        try:
            self.job.status = status
            self.job.end_time = datetime.utcnow()
            self.job.records_fetched = records
            self.job.error_message = error
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to close job: {e}")
        finally:
            self.db.close()

    def _generate_flight_id(self, icao24: str, callsign: str) -> str:
        today = datetime.utcnow().strftime('%Y-%m-%d')
        unique_string = f"{icao24}_{callsign.strip()}_{today}"
        return hashlib.md5(unique_string.encode()).hexdigest()

    def _get_or_create_airline(self, icao24: str, country: str = "Unknown") -> int:
        airline = self.db.query(Airline).filter(Airline.icao24 == icao24).first()
        if not airline:
            airline = Airline(icao24=icao24, name=f"Unknown ({icao24})")
            self.db.add(airline)
            self.db.commit()
            self.db.refresh(airline)
        return airline.id


class RealtimeEngine(BaseEngine):
    def __init__(self, bbox: Dict[str, float]):
        super().__init__(JobMode.REALTIME, bbox)

    def run(self):
        try:
            states = self.client.get_live_states_by_bbox(**self.params)
            if not states:
                self._close_job(JobStatus.SUCCESS, 0)
                return

            current_time = int(time.time())
            processed = 0

            for state in states:
                icao24 = str(state[0]).strip().lower()
                callsign = str(state[1]).strip() if state[1] else ""
                origin_country = str(state[2]).strip() if state[2] else "Unknown"
                lon, lat, alt, on_ground = state[5], state[6], state[7], state[8]

                if lon is None or lat is None:
                    continue

                unique_id = self._generate_flight_id(icao24, callsign)
                traj_point = {"ts": current_time, "lon": lon, "lat": lat, "alt": alt}

                flight = self.db.query(Flight).filter(Flight.unique_flight_id == unique_id).first()

                if flight:
                    current_traj = flight.trajectory or []
                    if not current_traj or (current_traj[-1]['lon'] != lon or current_traj[-1]['lat'] != lat):
                        current_traj.append(traj_point)
                        flight.trajectory = current_traj
                        flag_modified(flight, "trajectory")
                        flight.last_seen = current_time
                        
                        if on_ground and not flight.est_arrival_airport:
                            event = FlightEvent(flight_id=flight.id, event_type="landing", timestamp=current_time, data={"lon": lon, "lat": lat})
                            self.db.add(event)
                else:
                    airline_id = self._get_or_create_airline(icao24, origin_country)
                    flight = Flight(
                        icao24=icao24, callsign=callsign, airline_id=airline_id,
                        origin_country=origin_country, first_seen=current_time, last_seen=current_time,
                        unique_flight_id=unique_id, trajectory=[traj_point]
                    )
                    self.db.add(flight)
                    self.db.flush()
                    
                    event_type = "takeoff" if not on_ground else "radar_entry"
                    event = FlightEvent(flight_id=flight.id, event_type=event_type, timestamp=current_time, data={"lon": lon, "lat": lat})
                    self.db.add(event)

                processed += 1
                if processed % 100 == 0:
                    self.db.commit()

            self.db.commit()
            self._close_job(JobStatus.SUCCESS, processed)

        except BaseException as e: # 🚀 Catch SoftTimeLimitExceeded and other base exceptions
            logger.error(f"Realtime Engine Error/Timeout: {e}", exc_info=True)
            self._close_job(JobStatus.FAILED, error=str(e))
            raise

class HistoricalEngine(BaseEngine):
    def __init__(self, start_ts: int, end_ts: int):
        super().__init__(JobMode.HISTORICAL, {"start_ts": start_ts, "end_ts": end_ts})

    def run(self):
        try:
            # Logic for historical backfill
            flights_data = self.client.get_historical_flights(self.params["start_ts"], self.params["end_ts"])
            # ... processing logic ...
            self._close_job(JobStatus.SUCCESS, len(flights_data))
        except BaseException as e:
            self._close_job(JobStatus.FAILED, error=str(e))
            raise