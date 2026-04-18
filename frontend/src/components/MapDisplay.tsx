import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Map as MapIcon, Loader2 } from 'lucide-react';
import { flightsApi } from '@/api/client';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// إصلاح مشكلة أيقونات Leaflet الافتراضية في React
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

interface MapDisplayProps {
  activeFlights: any[];
  loading: boolean;
}

export default function MapDisplay({ activeFlights, loading }: MapDisplayProps) {
  const [selectedFlightId, setSelectedFlightId] = useState<number | null>(null);
  const [trajectory, setTrajectory] = useState<any[]>([]);
  const [loadingTraj, setLoadingTraj] = useState(false);

  // مركز الخريطة الافتراضي (الشرق الأوسط)
  const defaultCenter: [number, number] = [25.0, 45.0];

  // جلب المسار عند النقر على طائرة
  const handleMarkerClick = async (flightId: number) => {
    setSelectedFlightId(flightId);
    setLoadingTraj(true);
    try {
      const trajData = await flightsApi.getFlightTrajectory(flightId);
      setTrajectory(trajData);
    } catch (error) {
      console.error("Failed to fetch trajectory", error);
      setTrajectory([]);
    } finally {
      setLoadingTraj(false);
    }
  };

  // تحويل بيانات المسار إلى صيغة يفهمها Leaflet (مصفوفة من [lat, lon])
  const polylinePositions = trajectory
    .filter(p => p.lat != null && p.lon != null)
    .map(p => [p.lat, p.lon] as [number, number]);

  return (
    <Card className="col-span-full shadow-md">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between text-lg">
          <div className="flex items-center gap-2">
            <MapIcon className="h-5 w-5 text-primary" />
            Live Radar & Trajectory Tracking
          </div>
          <div className="text-sm font-normal text-muted-foreground flex items-center gap-2">
            {loading && <Loader2 className="h-4 w-4 animate-spin" />}
            {activeFlights.length} Active Flights
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0 overflow-hidden rounded-b-xl">
        <div className="h-[500px] w-full relative z-0">
          <MapContainer 
            center={defaultCenter} 
            zoom={4} 
            scrollWheelZoom={true} 
            style={{ height: '100%', width: '100%' }}
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            
            {/* رسم الطائرات المحلقة */}
            {activeFlights.map((flight) => (
              flight.lat && flight.lon ? (
                <Marker 
                  key={flight.id} 
                  position={[flight.lat, flight.lon]}
                  eventHandlers={{
                    click: () => handleMarkerClick(flight.id),
                  }}
                >
                  <Popup>
                    <div className="font-semibold">{flight.callsign}</div>
                    <div className="text-xs text-gray-500">ICAO: {flight.icao24.toUpperCase()}</div>
                    <div className="text-xs">Alt: {flight.alt ? `${Math.round(flight.alt)}m` : 'N/A'}</div>
                    {loadingTraj && selectedFlightId === flight.id && (
                      <div className="text-xs text-blue-500 mt-1 flex items-center gap-1">
                        <Loader2 className="h-3 w-3 animate-spin" /> Loading path...
                      </div>
                    )}
                  </Popup>
                </Marker>
              ) : null
            ))}

            {/* رسم مسار الطائرة المحددة */}
            {selectedFlightId && polylinePositions.length > 0 && (
              <Polyline 
                positions={polylinePositions} 
                color="#3b82f6" 
                weight={3} 
                opacity={0.7} 
                dashArray="5, 10"
              />
            )}
          </MapContainer>
        </div>
      </CardContent>
    </Card>
  );
}