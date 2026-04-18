import { useState, useEffect, useCallback } from 'react';
import { flightsApi } from '@/api/client';

export const useMapData = (pollingIntervalMs = 15000) => {
  const [activeFlights, setActiveFlights] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMapData = useCallback(async () => {
    try {
      // لا نضع setLoading(true) هنا لكي لا تومض الخريطة كل 15 ثانية
      const data = await flightsApi.getActiveMapFlights();
      setActiveFlights(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch map data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMapData(); // الجلب الأولي
    
    // إعداد التحديث التلقائي (الرادار)
    const interval = setInterval(fetchMapData, pollingIntervalMs);
    return () => clearInterval(interval);
  }, [fetchMapData, pollingIntervalMs]);

  return { activeFlights, loading, error, refetch: fetchMapData };
};