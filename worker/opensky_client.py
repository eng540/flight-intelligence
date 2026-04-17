"""OpenSky API client for fetching flight data."""
import httpx
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import time
import os

logger = logging.getLogger(__name__)

# تعريف النطاقات الجغرافية المطلوبة (Bounding Boxes)
# التنسيق: [lamin, lomin, lamax, lomax]
REGIONS = {
    "middle_east": [12.0, 34.0, 42.0, 63.0],
    "central_asia": [35.0, 45.0, 55.0, 87.0],
    "north_africa": [15.0, -17.0, 37.0, 35.0]  # تصحيح: فقط شمال أفريقيا
}


class OpenSkyClient:
    """Client for OpenSky Network API."""

    BASE_URL = "https://opensky-network.org/api"

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        rate_limit_delay: float = 10.0
    ):
        """Initialize OpenSky client."""
        self.username = username or os.getenv("OPENSKY_USERNAME")
        self.password = password or os.getenv("OPENSKY_PASSWORD")
        self.client_id = client_id or os.getenv("OPENSKY_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("OPENSKY_CLIENT_SECRET")

        self.rate_limit_delay = rate_limit_delay
        self.last_request_time = 0
        self._token = None

        if self.username and self.password:
            self.rate_limit_delay = 2.0

    def _get_auth(self) -> Optional[tuple]:
        """Get authentication tuple if credentials are available."""
        if self.username and self.password:
            return (self.username, self.password)
        return None

    def _wait_for_rate_limit(self):
        """Wait to respect rate limits."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - elapsed
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict]:
        """Make authenticated request to OpenSky API."""
        self._wait_for_rate_limit()

        url = f"{self.BASE_URL}/{endpoint}"
        auth = self._get_auth()

        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.get(url, params=params, auth=auth)

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    logger.warning(f"No data found for request: {url}")
                    return None
                elif response.status_code == 429:
                    logger.warning("Rate limit exceeded, waiting 60s...")
                    time.sleep(60)
                    return None
                else:
                    logger.error(f"API request failed: {response.status_code} - {response.text}")
                    return None

        except httpx.TimeoutException:
            logger.error(f"Request timeout: {url}")
            return None
        except Exception as e:
            logger.error(f"Request error: {e}")
            return None

    # ==========================================
    # الدوال الأساسية
    # ==========================================

    def get_all_flights(self, begin: int, end: int) -> List[Dict[str, Any]]:
        """Get all flights within a time interval (global)."""
        if end - begin > 7200:
            logger.warning("Time interval too large, limiting to 2 hours")
            end = begin + 7200

        params = {"begin": begin, "end": end}
        data = self._make_request("flights/all", params)
        return data if data else []

    def get_flights_by_bounding_box(
        self,
        begin: int,
        end: int,
        lamin: float,
        lomin: float,
        lamax: float,
        lomax: float
    ) -> List[Dict[str, Any]]:
        """
        جلب الرحلات التاريخية ضمن مربع جغرافي محدد.
        يستخدم endpoint: /flights/all مع معاملات الإحداثيات.
        """
        if end - begin > 7200:
            logger.warning("Time interval > 2 hours, limiting to 2 hours")
            end = begin + 7200

        params = {
            "begin": begin,
            "end": end,
            "lamin": lamin,
            "lomin": lomin,
            "lamax": lamax,
            "lomax": lomax
        }
        data = self._make_request("flights/all", params)
        return data if data else []

    def get_flights_by_aircraft(self, icao24: str, begin: int, end: int) -> List[Dict[str, Any]]:
        """Get flights for a specific aircraft."""
        if end - begin > 172800:
            logger.warning("Time interval too large, limiting to 2 days")
            end = begin + 172800

        params = {"icao24": icao24.lower(), "begin": begin, "end": end}
        data = self._make_request("flights/aircraft", params)
        return data if data else []

    def get_arrivals_by_airport(self, airport: str, begin: int, end: int) -> List[Dict[str, Any]]:
        """Get arrivals for a specific airport."""
        params = {"airport": airport.upper(), "begin": begin, "end": end}
        data = self._make_request("flights/arrival", params)
        return data if data else []

    def get_departures_by_airport(self, airport: str, begin: int, end: int) -> List[Dict[str, Any]]:
        """Get departures for a specific airport."""
        params = {"airport": airport.upper(), "begin": begin, "end": end}
        data = self._make_request("flights/departure", params)
        return data if data else []

    def get_recent_flights(self, hours: int = 2, region: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get flights from the recent past.
        إذا حُددت المنطقة، يستخدم Bounding Box؛ وإلا يجلب عالمياً.
        """
        end = int(datetime.utcnow().timestamp())
        begin = end - (hours * 3600)

        if region and region in REGIONS:
            bbox = REGIONS[region]
            return self.get_flights_by_bounding_box(begin, end, *bbox)

        return self.get_all_flights(begin, end)

    def get_state_vectors(
        self,
        icao24: Optional[List[str]] = None,
        lamin: Optional[float] = None,
        lomin: Optional[float] = None,
        lamax: Optional[float] = None,
        lomax: Optional[float] = None
    ) -> Dict[str, Any]:
        """Get current state vectors (aircraft positions)."""
        params = {}
        if icao24:
            params["icao24"] = [i.lower() for i in icao24]

        if all(v is not None for v in [lamin, lomin, lamax, lomax]):
            params.update({"lamin": lamin, "lomin": lomin, "lamax": lamax, "lomax": lomax})

        return self._make_request("states/all", params)

    def get_track_by_aircraft(self, icao24: str, time_param: int = 0) -> Optional[Dict[str, Any]]:
        """جلب مسار الرحلة (Trajectory) لطائرة معينة."""
        params = {"icao24": icao24.lower(), "time": time_param}
        return self._make_request("tracks/all", params)
