// Flight Types
export interface Flight {
  id: number;
  icao24: string;
  callsign: string | null;
  airline_id: number | null;
  airline?: Airline;
  origin_country: string | null;
  first_seen: number | null;
  last_seen: number | null;
  est_departure_airport: string | null;
  est_arrival_airport: string | null;
  est_departure_time: number | null;
  est_arrival_time: number | null;
  ingestion_time: string;
  duration_seconds: number | null;
  duration_minutes: number | null;
  duration_hours: number | null;
}

export interface Airline {
  id: number;
  icao24: string;
  name: string | null;
  callsign_prefix: string | null;
  country_id: number | null;
  country?: Country;
  created_at: string;
  flight_count?: number;
}

export interface Country {
  id: number;
  name: string;
  iso_code: string | null;
  created_at: string;
}

export interface FlightListResponse {
  total: number;
  page: number;
  page_size: number;
  pages: number;
  data: Flight[];
}

export interface FlightFilterParams {
  airline_id?: number;
  country?: string;
  date_from?: string;
  date_to?: string;
  departure_airport?: string;
  arrival_airport?: string;
  page?: number;
  page_size?: number;
}

// Statistics Types
export interface DailyFlightStats {
  date: string;
  flight_count: number;
}

export interface AirlineActivityStats {
  airline_icao24: string;
  airline_name: string | null;
  flight_count: number;
}

export interface CountryActivityStats {
  country_name: string;
  flight_count: number;
}

export interface FlightStatistics {
  total_flights: number;
  daily_stats: DailyFlightStats[];
  top_airlines: AirlineActivityStats[];
  top_countries: CountryActivityStats[];
  flights_today: number;
  flights_this_week: number;
  flights_this_month: number;
}

// Health Check
export interface HealthCheck {
  status: string;
  timestamp: string;
  database: string;
  version: string;
}

// API Response
export interface ApiResponse<T> {
  data: T;
  message?: string;
  error?: string;
}
