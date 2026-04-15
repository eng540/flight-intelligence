import axios, { AxiosInstance, AxiosError } from 'axios';
import { 
  FlightListResponse, 
  FlightFilterParams, 
  FlightStatistics, 
  HealthCheck,
  Airline 
} from '@/types';

// API base URL
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Create axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error: AxiosError) => {
    console.error('API Response Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// Flights API
export const flightsApi = {
  // Get all flights with pagination
  getFlights: async (page: number = 1, pageSize: number = 50): Promise<FlightListResponse> => {
    const response = await apiClient.get('/flights', {
      params: { page, page_size: pageSize },
    });
    return response.data;
  },

  // Filter flights
  filterFlights: async (params: FlightFilterParams): Promise<FlightListResponse> => {
    const response = await apiClient.get('/flights/filter', { params });
    return response.data;
  },

  // Get flight by ID
  getFlight: async (id: number) => {
    const response = await apiClient.get(`/flights/${id}`);
    return response.data;
  },

  // Export flights to Excel
  exportFlights: async (params: FlightFilterParams): Promise<Blob> => {
    const response = await apiClient.get('/flights/export/excel', {
      params,
      responseType: 'blob',
    });
    return response.data;
  },
};

// Airlines API
export const airlinesApi = {
  // Get all airlines
  getAirlines: async (skip: number = 0, limit: number = 100): Promise<Airline[]> => {
    const response = await apiClient.get('/airlines', {
      params: { skip, limit },
    });
    return response.data;
  },

  // Get airline by ID
  getAirline: async (id: number): Promise<Airline> => {
    const response = await apiClient.get(`/airlines/${id}`);
    return response.data;
  },
};

// Statistics API
export const statsApi = {
  // Get comprehensive statistics
  getStatistics: async (): Promise<FlightStatistics> => {
    const response = await apiClient.get('/stats');
    return response.data;
  },

  // Get airline statistics
  getAirlineStats: async (limit: number = 10) => {
    const response = await apiClient.get('/stats/airlines', {
      params: { limit },
    });
    return response.data;
  },

  // Health check
  healthCheck: async (): Promise<HealthCheck> => {
    const response = await apiClient.get('/stats/health');
    return response.data;
  },
};

export default apiClient;
