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
    "north_africa": [0.0, -17.0, 37.0, 51.0]
}

class OpenSkyClient:
    """Client for OpenSky Network API."""
    
    BASE_URL = "https://opensky-network.org/api"
    
    def __init__(self, rate_limit_delay: float = 10.0):
        self.username = os.getenv("OPENSKY_USERNAME")
        self.password = os.getenv("OPENSKY_PASSWORD")
        self.rate_limit_delay = 2.0 if (self.username and self.password) else rate_limit_delay
        self.last_request_time = 0
    
    def _get_auth(self) -> Optional[tuple]:
        if self.username and self.password:
            return (self.username, self.password)
        return None
    
    def _wait_for_rate_limit(self):
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict]:
        self._wait_for_rate_limit()
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.get(url, params=params, auth=self._get_auth())
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    return None
                elif response.status_code == 429:
                    logger.warning("Rate limit exceeded, waiting 60s...")
                    time.sleep(60)
                    return None
                else:
                    logger.error(f"API request failed: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Request error: {e}")
            return None

    def get_flights_by_time(self, begin: int, end: int) -> List[Dict[str, Any]]:
        """جلب جميع الرحلات في فترة زمنية محددة (أقصاها ساعتين)"""
        if end - begin > 7200:
            logger.warning("Interval > 2 hours. Limiting to 2 hours.")
            end = begin + 7200
            
        params = {"begin": begin, "end": end}
        data = self._make_request("flights/all", params)
        return data if data else []

    def get_track_by_aircraft(self, icao24: str, time_param: int = 0) -> Optional[Dict[str, Any]]:
        """جلب مسار الرحلة (Trajectory) لطائرة معينة"""
        params = {"icao24": icao24.lower(), "time": time_param}
        return self._make_request("tracks/all", params)

    def get_recent_flights(self, hours: int = 2) -> List[Dict[str, Any]]:
        end = int(datetime.utcnow().timestamp())
        begin = end - (hours * 3600)
        return self.get_flights_by_time(begin, end)