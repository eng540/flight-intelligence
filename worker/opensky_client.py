"""OpenSky API client for fetching flight data."""
import httpx
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import time
import os

logger = logging.getLogger(__name__)


class OpenSkyClient:
    """Client for OpenSky Network API."""
    
    BASE_URL = "https://opensky-network.org/api"
    
    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        rate_limit_delay: float = 10.0  # seconds between requests for anonymous users
    ):
        """Initialize OpenSky client.
        
        Args:
            username: OpenSky username (optional)
            password: OpenSky password (optional)
            client_id: OAuth client ID (optional)
            client_secret: OAuth client secret (optional)
            rate_limit_delay: Delay between requests in seconds
        """
        self.username = username or os.getenv("OPENSKY_USERNAME")
        self.password = password or os.getenv("OPENSKY_PASSWORD")
        self.client_id = client_id or os.getenv("OPENSKY_CLIENT_ID")
        self.client_secret = client_id or os.getenv("OPENSKY_CLIENT_SECRET")
        self.rate_limit_delay = rate_limit_delay
        self.last_request_time = 0
        self._token = None
        
        # Use shorter delay if authenticated
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
        """Make authenticated request to OpenSky API.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            JSON response or None if request failed
        """
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
                    logger.warning("Rate limit exceeded, waiting longer...")
                    time.sleep(30)
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
    
    def get_all_flights(
        self,
        begin: int,
        end: int
    ) -> List[Dict[str, Any]]:
        """Get all flights within a time interval.
        
        Args:
            begin: Start time as Unix timestamp
            end: End time as Unix timestamp
            
        Returns:
            List of flight data dictionaries
        """
        # Validate time interval (max 2 hours for this endpoint)
        if end - begin > 7200:
            logger.warning("Time interval too large, limiting to 2 hours")
            end = begin + 7200
        
        params = {
            "begin": begin,
            "end": end
        }
        
        data = self._make_request("flights/all", params)
        return data if data else []
    
    def get_flights_by_aircraft(
        self,
        icao24: str,
        begin: int,
        end: int
    ) -> List[Dict[str, Any]]:
        """Get flights for a specific aircraft.
        
        Args:
            icao24: Aircraft ICAO 24-bit address
            begin: Start time as Unix timestamp
            end: End time as Unix timestamp
            
        Returns:
            List of flight data dictionaries
        """
        # Validate time interval (max 2 days for this endpoint)
        if end - begin > 172800:
            logger.warning("Time interval too large, limiting to 2 days")
            end = begin + 172800
        
        params = {
            "icao24": icao24.lower(),
            "begin": begin,
            "end": end
        }
        
        data = self._make_request("flights/aircraft", params)
        return data if data else []
    
    def get_arrivals_by_airport(
        self,
        airport: str,
        begin: int,
        end: int
    ) -> List[Dict[str, Any]]:
        """Get arrivals for a specific airport.
        
        Args:
            airport: Airport ICAO code
            begin: Start time as Unix timestamp
            end: End time as Unix timestamp
            
        Returns:
            List of flight data dictionaries
        """
        params = {
            "airport": airport.upper(),
            "begin": begin,
            "end": end
        }
        
        data = self._make_request("flights/arrival", params)
        return data if data else []
    
    def get_departures_by_airport(
        self,
        airport: str,
        begin: int,
        end: int
    ) -> List[Dict[str, Any]]:
        """Get departures for a specific airport.
        
        Args:
            airport: Airport ICAO code
            begin: Start time as Unix timestamp
            end: End time as Unix timestamp
            
        Returns:
            List of flight data dictionaries
        """
        params = {
            "airport": airport.upper(),
            "begin": begin,
            "end": end
        }
        
        data = self._make_request("flights/departure", params)
        return data if data else []
    
    def get_recent_flights(self, hours: int = 2) -> List[Dict[str, Any]]:
        """Get flights from the recent past.
        
        Args:
            hours: Number of hours to look back (max 2 for anonymous users)
            
        Returns:
            List of flight data dictionaries
        """
        end = int(datetime.utcnow().timestamp())
        begin = end - (hours * 3600)
        return self.get_all_flights(begin, end)
    
    def get_state_vectors(
        self,
        icao24: Optional[List[str]] = None,
        lamin: Optional[float] = None,
        lomin: Optional[float] = None,
        lamax: Optional[float] = None,
        lomax: Optional[float] = None
    ) -> Dict[str, Any]:
        """Get current state vectors (aircraft positions).
        
        Args:
            icao24: List of ICAO 24-bit addresses to filter
            lamin: Minimum latitude for bounding box
            lomin: Minimum longitude for bounding box
            lamax: Maximum latitude for bounding box
            lomax: Maximum longitude for bounding box
            
        Returns:
            State vectors data
        """
        params = {}
        
        if icao24:
            params["icao24"] = [i.lower() for i in icao24]
        
        if all(v is not None for v in [lamin, lomin, lamax, lomax]):
            params.update({
                "lamin": lamin,
                "lomin": lomin,
                "lamax": lamax,
                "lomax": lomax
            })
        
        return self._make_request("states/all", params)
