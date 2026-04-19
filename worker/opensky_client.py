"""OpenSky API client for fetching flight data."""
import httpx
import logging
from typing import List, Dict, Any, Optional
import time
import os

logger = logging.getLogger(__name__)

class OpenSkyClient:
    """Client for OpenSky Network API with strict rate limiting."""
    
    BASE_URL = "https://opensky-network.org/api"
    
    def __init__(self):
        self.username = os.getenv("OPENSKY_USERNAME")
        self.password = os.getenv("OPENSKY_PASSWORD")
        # OpenSky Limits: Anonymous=10s, Authenticated=5s for /states
        self.rate_limit_delay = 5.0 if self.username else 10.0
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
            # 🚀 الإصلاح الجذري: زيادة الـ timeout إلى 60 ثانية لتجنب أخطاء الشبكة
            with httpx.Client(timeout=60.0) as client:
                response = client.get(url, params=params, auth=self._get_auth())
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    logger.warning("OpenSky Rate limit exceeded. Backing off for 60s.")
                    time.sleep(60)
                    return None
                elif response.status_code == 404:
                    return None
                else:
                    logger.error(f"API Error {response.status_code}: {response.text}")
                    return None
        except Exception as e:
            logger.error(f"HTTP Request failed: {e}")
            return None

    def get_live_states_by_bbox(self, lamin: float, lomin: float, lamax: float, lomax: float) -> List[list]:
        """يجلب لقطة الرادار الحالية (State Vectors) للمنطقة المحددة."""
        params = {"lamin": lamin, "lomin": lomin, "lamax": lamax, "lomax": lomax}
        data = self._make_request("states/all", params)
        return data.get("states", []) if data else []

    def get_historical_flights(self, begin: int, end: int) -> List[Dict[str, Any]]:
        """يجلب الرحلات التاريخية المكتملة."""
        params = {"begin": begin, "end": end}
        data = self._make_request("flights/all", params)
        return data if data else []