import { useState, Suspense, lazy } from 'react';
import { Toaster } from '@/components/ui/sonner';
import { Header } from '@/sections/Header';
import { StatsCards } from '@/sections/StatsCards';
import { ChartsSection } from '@/sections/ChartsSection';
import { FlightsTable } from '@/sections/FlightsTable';
import { FilterSection } from '@/sections/FilterSection';
import { useStatistics } from '@/hooks/useStatistics';
import { useFilteredFlights } from '@/hooks/useFlights';
import { useMapData } from '@/hooks/useMapData';
import { FlightFilterParams } from '@/types';
import { Loader2 } from 'lucide-react';
import './App.css';

// Lazy load the map component to improve initial page load performance
const MapDisplay = lazy(() => import('@/components/MapDisplay'));

function App() {
  const [filters, setFilters] = useState<FlightFilterParams>({
    page: 1,
    page_size: 50,
  });

  const { data: stats, loading: statsLoading, refetch: refetchStats } = useStatistics();
  const { data: flightsData, loading: flightsLoading, refetch: refetchFlights } = useFilteredFlights(filters);
  const { activeFlights, loading: mapLoading, refetch: refetchMap } = useMapData();

  const handleRefresh = () => {
    refetchStats();
    refetchFlights();
    refetchMap();
  };

  const handleFilterChange = (newFilters: FlightFilterParams) => {
    setFilters({ ...newFilters, page: 1 });
  };

  const handlePageChange = (page: number) => {
    setFilters({ ...filters, page });
  };

  return (
    <div className="min-h-screen bg-background">
      <Toaster position="top-right" richColors />
      
      {/* ✅ تم التعديل هنا: حذف mapLoading */}
      <Header 
        onRefresh={handleRefresh} 
        loading={statsLoading || flightsLoading} 
      />
      
      <main className="container mx-auto px-4 py-6 space-y-6">
        <StatsCards stats={stats} loading={statsLoading} />
        
        {/* Interactive Map Section */}
        <Suspense fallback={
          <div className="h-[500px] w-full flex flex-col items-center justify-center border rounded-xl bg-muted/20">
            <Loader2 className="h-8 w-8 animate-spin text-primary mb-4" />
            <span className="text-muted-foreground font-medium">Loading Interactive Radar...</span>
          </div>
        }>
          <MapDisplay activeFlights={activeFlights} loading={mapLoading} />
        </Suspense>

        <ChartsSection stats={stats} loading={statsLoading} />
        
        <FilterSection 
          filters={filters} 
          onFilterChange={handleFilterChange} 
        />
        
        <FlightsTable 
          data={flightsData}
          loading={flightsLoading}
          filters={filters}
          onFilterChange={handleFilterChange}
          onPageChange={handlePageChange}
        />
      </main>
      
      <footer className="border-t mt-12 py-6">
        <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
          <p>Flight Intelligence Dashboard &copy; {new Date().getFullYear()}</p>
          <p className="mt-1">Data provided by OpenSky Network</p>
        </div>
      </footer>
    </div>
  );
}

export default App;