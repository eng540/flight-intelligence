import axios, { AxiosInstance, AxiosError } from 'axios';
import { 
  FlightListResponse, 
  FlightFilterParams, 
  FlightStatistics, 
  HealthCheck,
  Airline 
} from '@/types';

// API base URL
const API_BASE_URL = ''; // مسار فارغ يعني أن الـ API موجود على نفس الدومين
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
  getFlights: async (page: number = 1, pageSize: number = 50): Promise<FlightListResponse> => {
    const response = await apiClient.get('/flights', {
      params: { page, page_size: pageSize },
    });
    return response.data;
  },

  filterFlights: async (params: FlightFilterParams): Promise<FlightListResponse> => {
    const response = await apiClient.get('/flights/filter', { params });
    return response.data;
  },

  getFlight: async (id: number) => {
    const response = await apiClient.get(`/flights/${id}`);
    return response.data;
  },

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
  getAirlines: async (skip: number = 0, limit: number = 100): Promise<Airline[]> => {
    const response = await apiClient.get('/airlines', {
      params: { skip, limit },
    });
    return response.data;
  },

  getAirline: async (id: number): Promise<Airline> => {
    const response = await apiClient.get(`/airlines/${id}`);
    return response.data;
  },
};

// Statistics API
export const statsApi = {
  getStatistics: async (): Promise<FlightStatistics> => {
    const response = await apiClient.get('/stats');
    return response.data;
  },

  getAirlineStats: async (limit: number = 10) => {
    const response = await apiClient.get('/stats/airlines', {
      params: { limit },
    });
    return response.data;
  },

  healthCheck: async (): Promise<HealthCheck> => {
    const response = await apiClient.get('/stats/health');
    return response.data;
  },
};

export default apiClient;