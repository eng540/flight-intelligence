"""CRUD operations for the Flight Intelligence database."""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, desc
from sqlalchemy.exc import IntegrityError
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from app import models, schemas

logger = logging.getLogger(__name__)


class CountryCRUD:
    @staticmethod
    def get_by_id(db: Session, country_id: int) -> Optional[models.Country]:
        return db.query(models.Country).filter(models.Country.id == country_id).first()

    @staticmethod
    def get_by_name(db: Session, name: str) -> Optional[models.Country]:
        return db.query(models.Country).filter(
            func.lower(models.Country.name) == func.lower(name)
        ).first()

    @staticmethod
    def get_or_create(db: Session, name: str) -> models.Country:
        country = CountryCRUD.get_by_name(db, name)
        if not country:
            country = models.Country(name=name)
            db.add(country)
            try:
                db.commit()
                db.refresh(country)
            except IntegrityError:
                db.rollback()
                country = CountryCRUD.get_by_name(db, name)
        return country

    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100) -> List[models.Country]:
        return db.query(models.Country).offset(skip).limit(limit).all()


class AirlineCRUD:
    @staticmethod
    def get_by_id(db: Session, airline_id: int) -> Optional[models.Airline]:
        return db.query(models.Airline).options(
            joinedload(models.Airline.country)
        ).filter(models.Airline.id == airline_id).first()

    @staticmethod
    def get_by_icao24(db: Session, icao24: str) -> Optional[models.Airline]:
        return db.query(models.Airline).options(
            joinedload(models.Airline.country)
        ).filter(models.Airline.icao24 == icao24.lower()).first()

    @staticmethod
    def get_or_create(db: Session, icao24: str, name: Optional[str] = None, country_name: Optional[str] = None) -> models.Airline:
        airline = AirlineCRUD.get_by_icao24(db, icao24)
        if not airline:
            country_id = None
            if country_name:
                country = CountryCRUD.get_or_create(db, country_name)
                country_id = country.id

            airline = models.Airline(
                icao24=icao24.lower(),
                name=name,
                country_id=country_id
            )
            db.add(airline)
            try:
                db.commit()
                db.refresh(airline)
            except IntegrityError:
                db.rollback()
                airline = AirlineCRUD.get_by_icao24(db, icao24)
        return airline

    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100) -> List[models.Airline]:
        return db.query(models.Airline).options(
            joinedload(models.Airline.country)
        ).offset(skip).limit(limit).all()

    @staticmethod
    def get_most_active(db: Session, limit: int = 10) -> List[Dict[str, Any]]:
        results = db.query(
            models.Airline.icao24,
            models.Airline.name,
            func.count(models.Flight.id).label('flight_count')
        ).join(models.Flight, models.Airline.id == models.Flight.airline_id, isouter=True
        ).group_by(models.Airline.id, models.Airline.icao24, models.Airline.name
        ).order_by(desc('flight_count')
        ).limit(limit).all()

        return [
            {
                "airline_icao24": r.icao24,
                "airline_name": r.name,
                "flight_count": r.flight_count
            }
            for r in results
        ]


class FlightCRUD:
    @staticmethod
    def get_by_id(db: Session, flight_id: int) -> Optional[models.Flight]:
        return db.query(models.Flight).options(
            joinedload(models.Flight.airline)
        ).filter(models.Flight.id == flight_id).first()

    @staticmethod
    def get_by_unique_id(db: Session, unique_flight_id: str) -> Optional[models.Flight]:
        return db.query(models.Flight).filter(
            models.Flight.unique_flight_id == unique_flight_id
        ).first()

    @staticmethod
    def exists(db: Session, unique_flight_id: str) -> bool:
        return db.query(models.Flight).filter(
            models.Flight.unique_flight_id == unique_flight_id
        ).first() is not None

    @staticmethod
    def get_all(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        airline_id: Optional[int] = None,
        country: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        departure_airport: Optional[str] = None,
        arrival_airport: Optional[str] = None
    ) -> tuple[List[models.Flight], int]:
        query = db.query(models.Flight).options(
            joinedload(models.Flight.airline)
        )

        if airline_id:
            query = query.filter(models.Flight.airline_id == airline_id)

        if country:
            query = query.filter(
                func.lower(models.Flight.origin_country) == func.lower(country)
            )

        if date_from:
            try:
                from_date = datetime.strptime(date_from, "%Y-%m-%d")
                from_timestamp = int(from_date.timestamp())
                query = query.filter(models.Flight.first_seen >= from_timestamp)
            except ValueError:
                logger.warning(f"Invalid date_from format: {date_from}")

        if date_to:
            try:
                to_date = datetime.strptime(date_to, "%Y-%m-%d")
                to_timestamp = int(to_date.timestamp())
                query = query.filter(models.Flight.last_seen <= to_timestamp)
            except ValueError:
                logger.warning(f"Invalid date_to format: {date_to}")

        if departure_airport:
            query = query.filter(
                func.upper(models.Flight.est_departure_airport) == departure_airport.upper()
            )

        if arrival_airport:
            query = query.filter(
                func.upper(models.Flight.est_arrival_airport) == arrival_airport.upper()
            )

        total = query.count()
        flights = query.order_by(desc(models.Flight.first_seen)).offset(skip).limit(limit).all()
        return flights, total

    # ✅ الجديد: الاستعلام الجغرافي الزمني
    @staticmethod
    def get_by_bounding_box(
        db: Session,
        lamin: float,
        lomin: float,
        lamax: float,
        lomax: float,
        begin: int,
        end: int,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[models.Flight], int]:
        """
        جلب الرحلات ضمن مربع جغرافي وفترة زمنية.
        يفحص المسار (trajectory) للتحديد الجغرافي.
        """
        query = db.query(models.Flight).options(
            joinedload(models.Flight.airline)
        ).filter(
            models.Flight.first_seen >= begin,
            models.Flight.last_seen <= end,
            models.Flight.trajectory.isnot(None)
        )

        flights = query.order_by(desc(models.Flight.first_seen)).all()

        # فلترة جغرافية في الذاكرة (حتى تركيب PostGIS مستقبلاً)
        filtered = []
        for flight in flights:
            if flight.trajectory:
                for point in flight.trajectory:
                    lat = point.get('lat')
                    lon = point.get('lon')
                    if lat is not None and lon is not None:
                        if lamin <= lat <= lamax and lomin <= lon <= lomax:
                            filtered.append(flight)
                            break

        total = len(filtered)
        paginated = filtered[skip:skip + limit]
        return paginated, total

    # ✅ الجديد: تحليلات الدول الأكثر نشاطاً
    @staticmethod
    def get_top_countries_in_geo_time(
        db: Session,
        begin: int,
        end: int,
        lamin: float,
        lomin: float,
        lamax: float,
        lomax: float,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """الدول الأكثر نشاطاً ضمن نطاق جغرافي وزمني."""
        flights, _ = FlightCRUD.get_by_bounding_box(
            db, lamin, lomin, lamax, lomax, begin, end, skip=0, limit=10000
        )

        country_counts: Dict[str, int] = {}
        for flight in flights:
            country = flight.origin_country or "Unknown"
            country_counts[country] = country_counts.get(country, 0) + 1

        sorted_countries = sorted(
            country_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]

        return [
            {"country_name": name, "flight_count": count}
            for name, count in sorted_countries
        ]

    @staticmethod
    def create_or_update(db: Session, flight_data: schemas.FlightCreate) -> Optional[models.Flight]:
        existing = FlightCRUD.get_by_unique_id(db, flight_data.unique_flight_id)

        if existing:
            update_data = flight_data.model_dump(exclude={'unique_flight_id'})
            for key, value in update_data.items():
                setattr(existing, key, value)
            db.commit()
            db.refresh(existing)
            return existing

        flight = models.Flight(**flight_data.model_dump())
        db.add(flight)
        try:
            db.commit()
            db.refresh(flight)
            return flight
        except IntegrityError as e:
            db.rollback()
            logger.warning(f"Integrity error creating flight: {e}")
            return None

    @staticmethod
    def get_statistics(db: Session) -> Dict[str, Any]:
        now = datetime.utcnow()
        today_start = int(datetime(now.year, now.month, now.day).timestamp())
        week_start = int((now - timedelta(days=7)).timestamp())
        month_start = int((now - timedelta(days=30)).timestamp())

        total_flights = db.query(models.Flight).count()
        flights_today = db.query(models.Flight).filter(
            models.Flight.first_seen >= today_start
        ).count()
        flights_this_week = db.query(models.Flight).filter(
            models.Flight.first_seen >= week_start
        ).count()
        flights_this_month = db.query(models.Flight).filter(
            models.Flight.first_seen >= month_start
        ).count()

        daily_stats = []
        for i in range(7):
            day = now - timedelta(days=i)
            day_start = int(datetime(day.year, day.month, day.day).timestamp())
            day_end = day_start + 86400
            count = db.query(models.Flight).filter(
                and_(
                    models.Flight.first_seen >= day_start,
                    models.Flight.first_seen < day_end
                )
            ).count()
            daily_stats.append({
                "date": day.strftime("%Y-%m-%d"),
                "flight_count": count
            })
        daily_stats.reverse()

        top_airlines = db.query(
            models.Airline.icao24,
            models.Airline.name,
            func.count(models.Flight.id).label('flight_count')
        ).join(models.Flight, models.Airline.id == models.Flight.airline_id
        ).group_by(models.Airline.id, models.Airline.icao24, models.Airline.name
        ).order_by(desc('flight_count')
        ).limit(10).all()

        top_countries = db.query(
            models.Flight.origin_country,
            func.count(models.Flight.id).label('flight_count')
        ).group_by(models.Flight.origin_country
        ).order_by(desc('flight_count')
        ).limit(10).all()

        return {
            "total_flights": total_flights,
            "daily_stats": daily_stats,
            "top_airlines": [
                {
                    "airline_icao24": a.icao24,
                    "airline_name": a.name,
                    "flight_count": a.flight_count
                }
                for a in top_airlines
            ],
            "top_countries": [
                {
                    "country_name": c.origin_country or "Unknown",
                    "flight_count": c.flight_count
                }
                for c in top_countries
            ],
            "flights_today": flights_today,
            "flights_this_week": flights_this_week,
            "flights_this_month": flights_this_month
        }

    @staticmethod
    def delete_old_flights(db: Session, cutoff_timestamp: int) -> int:
        result = db.query(models.Flight).filter(
            models.Flight.last_seen < cutoff_timestamp
        ).delete(synchronize_session=False)
        db.commit()
        return result
