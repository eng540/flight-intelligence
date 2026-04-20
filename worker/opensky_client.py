"""OpenSky API client for fetching flight data."""
import httpx
import logging
from typing import List, Dict, Any, Optional
import time
import os

logger = logging.getLogger(__name__)

class OpenSkyClient:
    """Client for OpenSky Network API."""
    
    BASE_URL = "https://opensky-network.org/api"
    
    def __init__(self):
        self.username = os.getenv("OPENSKY_USERNAME")
        self.password = os.getenv("OPENSKY_PASSWORD")
        
        # 2.0 seconds for authenticated users, 10.0 for anonymous
        self.rate_limit_delay = 2.0 if self.username and self.password else 10.0
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
            # 🚀 Increased timeout to 120.0 seconds to handle large areas/slow responses
            with httpx.Client(timeout=120.0) as client:
                response = client.get(url, params=params, auth=self._get_auth())
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    return None
                elif response.status_code == 429:
                    logger.warning("Rate limit exceeded, waiting longer...")
                    time.sleep(30)
                    return None
                else:
                    logger.error(f"API request failed: {response.status_code} - {response.text}")
                    # 🚀 Raise exception instead of returning None to prevent silent failures
                    raise Exception(f"OpenSky API Error: {response.status_code} - {response.text}")
                    
        except httpx.TimeoutException as e:
            logger.error(f"Request timeout: {url}")
            # 🚀 Propagate the timeout exception to mark the job as FAILED
            raise Exception("OpenSky API Timeout: Area might be too large or server is slow.") from e
        except Exception as e:
            logger.error(f"Request error: {e}")
            raise e

    def get_live_states_by_bbox(self, lamin: float, lomin: float, lamax: float, lomax: float) -> List[list]:
        """Get live radar states for a specific bounding box."""
        params = {
            "lamin": lamin,
            "lomin": lomin,
            "lamax": lamax,
            "lomax": lomax
        }
        data = self._make_request("states/all", params)
        return data.get("states", []) if data else []

    def get_historical_flights(self, begin: int, end: int) -> List[Dict[str, Any]]:
        """Get historical flights."""
        params = {"begin": begin, "end": end}
        data = self._make_request("flights/all", params)
        return data if data else []

    def get_recent_flights(self, hours: int = 2) -> List[Dict[str, Any]]:
        """Get flights from recent hours."""
        end = int(time.time())
        begin = end - (hours * 3600)
        return self.get_historical_flights(begin, end)

    def get_all_flights(self, begin: int, end: int) -> List[Dict[str, Any]]:
        """Get all flights within a time range."""
        return self.get_historical_flights(begin, end)