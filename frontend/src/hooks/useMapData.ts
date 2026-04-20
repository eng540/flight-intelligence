import { useState, useEffect, useCallback } from 'react';
import { flightsApi } from '@/api/client';

// 🚀 التعديل المعماري: تغيير معدل التحديث إلى 60 ثانية (60000ms) بدلاً من 15 ثانية.
// بما أن الرادار في الباك إند يعمل كل 5 دقائق، لا حاجة لإرهاق الخادم بطلبات كل 15 ثانية.
// 60 ثانية كافية جداً لإعطاء المستخدم إحساساً بالتحديث المستمر دون ضغط على الـ API.
export const useMapData = (pollingIntervalMs = 60000) => {
  const [activeFlights, setActiveFlights] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMapData = useCallback(async () => {
    try {
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
    fetchMapData();
    const interval = setInterval(fetchMapData, pollingIntervalMs);
    return () => clearInterval(interval);
  }, [fetchMapData, pollingIntervalMs]);

  return { activeFlights, loading, error, refetch: fetchMapData };
};