"""Flight data ingestion service."""
import logging
import sys
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from worker.opensky_client import OpenSkyClient, REGIONS
from worker.data_processor import FlightDataProcessor
from app.database import SessionLocal
from app.crud import FlightCRUD, AirlineCRUD
from app.schemas import FlightCreate
from app.models import IngestionLog

logger = logging.getLogger(__name__)


class FlightIngestionService:
    """Service for ingesting flight data from OpenSky API."""

    def __init__(self):
        self.client = OpenSkyClient()
        self.processor = FlightDataProcessor()
        self.db = None

    def __enter__(self):
        self.db = SessionLocal()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.db:
            self.db.close()

    def ingest_recent_flights(self, hours: int = 2, region: Optional[str] = None) -> Dict[str, int]:
        """
        جلب الرحلات الحديثة (للتشغيل الدوري كل 5 دقائق).
        يستخدم Bounding Box إذا حُددت المنطقة.
        """
        logger.info(f"Starting ingestion for last {hours} hours (region: {region or 'global'})")

        try:
            flights_data = self.client.get_recent_flights(hours, region=region)
            if not flights_data:
                logger.info("No flights found in recent hours.")
                return {"created": 0, "updated": 0, "skipped": 0}

            processed_flights = self.processor.process_flights(flights_data)
            unique_flights = self.processor.remove_duplicates(processed_flights)

            # للاستيعاب اللحظي: لا نجلب المسارات لتوفير الوقت
            stats = self._ingest_flights(unique_flights)
            return stats

        except Exception as e:
            logger.error(f"Error during recent ingestion: {e}", exc_info=True)
            return {"created": 0, "updated": 0, "skipped": 0, "error": str(e)}

    def ingest_historical_data_chunked(
        self,
        start_date: str,
        end_date: str,
        region_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        محرك الجلب التاريخي الذكي.
        يقوم بتقسيم الفترة إلى أيام، يتتبع الحالة عبر IngestionLog.
        """
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            return {"error": "Invalid date format. Use YYYY-MM-DD."}

        if start_dt >= end_dt:
            return {"error": "start_date must be before end_date."}

        total_stats = {
            "days_processed": 0, "created": 0, "updated": 0,
            "skipped": 0, "errors": 0
        }
        current_dt = start_dt

        logger.info(f"Starting historical ingestion from {start_date} to {end_date}. Region: {region_name or 'Global'}")

        while current_dt < end_dt:
            target_date_str = current_dt.strftime('%Y-%m-%d')
            next_dt = current_dt + timedelta(days=1)
            begin_ts = int(current_dt.timestamp())
            end_ts = int(next_dt.timestamp())

            # التحقق من سجل الحالة
            log_entry = self.db.query(IngestionLog).filter(
                IngestionLog.target_date == target_date_str,
                IngestionLog.region == region_name
            ).first()

            if log_entry and log_entry.status == "completed":
                logger.info(f"Skipping {target_date_str}: Already fully processed.")
                current_dt = next_dt
                continue

            if not log_entry:
                log_entry = IngestionLog(
                    target_date=target_date_str,
                    region=region_name,
                    status="pending"
                )
                self.db.add(log_entry)
            else:
                log_entry.status = "pending"
                log_entry.error_message = None

            self.db.commit()

            logger.info(f"Processing chunk: {target_date_str}")

            try:
                # جلب البيانات الجغرافية إذا حُددت المنطقة
                if region_name and region_name in REGIONS:
                    bbox = REGIONS[region_name]
                    all_flights = []
                    chunk_start = begin_ts
                    while chunk_start < end_ts:
                        chunk_end = min(chunk_start + 7200, end_ts)
                        chunk_data = self.client.get_flights_by_bounding_box(
                            chunk_start, chunk_end, *bbox
                        )
                        if chunk_data:
                            all_flights.extend(chunk_data)
                        chunk_start = chunk_end
                    flights_data = all_flights
                else:
                    flights_data = self.client.get_all_flights(begin_ts, end_ts)

                if not flights_data:
                    logger.info(f"No flights found for {target_date_str}")
                    log_entry.status = "completed"
                    log_entry.completed_at = datetime.utcnow()
                    log_entry.records_fetched = 0
                    self.db.commit()
                    current_dt = next_dt
                    continue

                processed_flights = self.processor.process_flights(flights_data)
                unique_flights = self.processor.remove_duplicates(processed_flights)

                # إثراء المسارات بحد أقصى 50 رحلة يومياً
                flights_with_tracks = self._enrich_with_trajectories(unique_flights, max_tracks=50)

                stats = self._ingest_flights(flights_with_tracks)

                log_entry.status = "completed"
                log_entry.completed_at = datetime.utcnow()
                log_entry.records_fetched = stats["created"] + stats["updated"]
                self.db.commit()

                total_stats["days_processed"] += 1
                total_stats["created"] += stats["created"]
                total_stats["updated"] += stats["updated"]
                total_stats["skipped"] += stats["skipped"]

                logger.info(f"Chunk {target_date_str} completed: {stats}")

            except Exception as e:
                logger.error(f"Error processing chunk {target_date_str}: {e}")
                log_entry.status = "failed"
                log_entry.error_message = str(e)
                self.db.commit()
                total_stats["errors"] += 1

            current_dt = next_dt

        logger.info(f"Historical ingestion finished. Total stats: {total_stats}")
        return total_stats

    def _enrich_with_trajectories(
        self,
        flights: List[Dict[str, Any]],
        max_tracks: int = 50
    ) -> List[Dict[str, Any]]:
        """إثراء بيانات الرحلات بمسار الطيران (بحد أقصى)."""
        enriched_flights = []
        track_count = 0

        for flight in flights:
            icao24 = flight.get("icao24")
            time_param = flight.get("first_seen", 0)

            if icao24 and track_count < max_tracks:
                track_data = self.client.get_track_by_aircraft(icao24, time_param)
                if track_data and "path" in track_data:
                    trajectory = [
                        {"time": p[0], "lat": p[1], "lon": p[2], "alt": p[3]}
                        for p in track_data["path"] if len(p) >= 4
                    ]
                    flight["trajectory"] = trajectory
                    track_count += 1
                else:
                    flight["trajectory"] = None
            else:
                flight["trajectory"] = None

            enriched_flights.append(flight)

        logger.info(f"Enriched {track_count} flights with trajectories.")
        return enriched_flights

    def _filter_by_bounding_box(
        self,
        flights: List[Dict[str, Any]],
        bbox: List[float]
    ) -> List[Dict[str, Any]]:
        """تصفية الرحلات جغرافياً بناءً على المسار."""
        lamin, lomin, lamax, lomax = bbox
        filtered_flights = []

        for flight in flights:
            trajectory = flight.get("trajectory")

            if trajectory:
                is_in_region = any(
                    lamin <= point.get("lat", 0) <= lamax and lomin <= point.get("lon", 0) <= lomax
                    for point in trajectory
                )
                if is_in_region:
                    filtered_flights.append(flight)
            else:
                filtered_flights.append(flight)

        logger.info(f"Geo-filtering: Kept {len(filtered_flights)} out of {len(flights)} flights.")
        return filtered_flights

    def _ingest_flights(self, flights: List[Dict[str, Any]]) -> Dict[str, int]:
        """حفظ الرحلات في قاعدة البيانات مع معالجة التكرار."""
        created = 0
        updated = 0
        skipped = 0

        for flight_data in flights:
            try:
                airline_info = self.processor.extract_airline_info(flight_data)
                if airline_info:
                    airline = AirlineCRUD.get_or_create(
                        self.db,
                        icao24=airline_info["icao24"],
                        country_name=airline_info.get("country_name")
                    )
                    flight_data["airline_id"] = airline.id

                flight_create = FlightCreate(**flight_data)

                existing = FlightCRUD.get_by_unique_id(
                    self.db,
                    flight_data["unique_flight_id"]
                )

                if existing:
                    update_data = flight_create.model_dump(exclude={'unique_flight_id'})
                    for key, value in update_data.items():
                        setattr(existing, key, value)
                    updated += 1
                else:
                    flight = FlightCRUD.create_or_update(self.db, flight_create)
                    if flight:
                        created += 1
                    else:
                        skipped += 1

                if (created + updated) % 50 == 0:
                    self.db.commit()

            except Exception as e:
                logger.error(f"Error ingesting flight {flight_data.get('unique_flight_id')}: {e}")
                skipped += 1
                continue

        self.db.commit()
        return {"created": created, "updated": updated, "skipped": skipped}

    def cleanup_old_data(self, days: int = 30) -> int:
        """
        ─── CLEANUP معطل — لا يحذف أي بيانات ───
        
        تم تعطيل هذه الوظيفة بناءً على متطلبات عدم حذف البيانات التاريخية.
        للتفعيل مستقبلاً:
        1. ألغِ التعليق على الكود أدناه
        2. فعّل المهمة في celery_app.py beat_schedule
        
        Returns:
            int: عدد السجلات المحذوفة (دائماً 0 عند التعطيل)
        """
        logger.warning(
            "cleanup_old_data() is DISABLED. "
            "No data will be deleted. "
            "To enable, uncomment the code below and activate in celery_app.py beat_schedule."
        )
        
        # ─── الكود الأصلي (معطل) ───
        # logger.info(f"Cleaning up flights older than {days} days")
        # cutoff = int((datetime.utcnow() - timedelta(days=days)).timestamp())
        # deleted = FlightCRUD.delete_old_flights(self.db, cutoff)
        # logger.info(f"Deleted {deleted} old flight records")
        # return deleted
        
        return 0  # لا شيء محذوف


def run_ingestion(hours: int = 2) -> Dict[str, int]:
    logging.basicConfig(level=logging.INFO)
    with FlightIngestionService() as service:
        return service.ingest_recent_flights(hours)


if __name__ == "__main__":
    stats = run_ingestion(hours=2)
    print(f"Ingestion stats: {stats}")
