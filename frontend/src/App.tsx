import { useState } from 'react';
import { Toaster } from '@/components/ui/sonner';
import { Header } from '@/sections/Header';
import { StatsCards } from '@/sections/StatsCards';
import { ChartsSection } from '@/sections/ChartsSection';
import { FlightsTable } from '@/sections/FlightsTable';
import { FilterSection } from '@/sections/FilterSection';
import { useStatistics } from '@/hooks/useStatistics';
import { useFilteredFlights } from '@/hooks/useFlights';
import { FlightFilterParams } from '@/types';
import './App.css';

function App() {
  // Filters state
  const [filters, setFilters] = useState<FlightFilterParams>({
    page: 1,
    page_size: 50,
  });

  // Data fetching
  const { 
    data: stats, 
    loading: statsLoading, 
    error: statsError, 
    refetch: refetchStats 
  } = useStatistics();

  const { 
    data: flightsData, 
    loading: flightsLoading, 
    error: flightsError, 
    refetch: refetchFlights 
  } = useFilteredFlights(filters);

  // Handle refresh
  const handleRefresh = () => {
    refetchStats();
    refetchFlights();
  };

  // Handle filter change
  const handleFilterChange = (newFilters: FlightFilterParams) => {
    setFilters({ ...newFilters, page: 1 });
  };

  // Handle page change
  const handlePageChange = (page: number) => {
    setFilters({ ...filters, page });
  };

  // Error handling
  if (statsError || flightsError) {
    console.error('Data fetching error:', statsError || flightsError);
  }

  return (
    <div className="min-h-screen bg-background">
      <Toaster position="top-right" richColors />
      
      <Header onRefresh={handleRefresh} loading={statsLoading || flightsLoading} />
      
      <main className="container mx-auto px-4 py-6 space-y-6">
        {/* Statistics Cards */}
        <StatsCards stats={stats} loading={statsLoading} />
        
        {/* Charts */}
        <ChartsSection stats={stats} loading={statsLoading} />
        
        {/* Filters */}
        <FilterSection 
          filters={filters} 
          onFilterChange={handleFilterChange} 
        />
        
        {/* Flights Table */}
        <FlightsTable 
          data={flightsData}
          loading={flightsLoading}
          filters={filters}
          onFilterChange={handleFilterChange}
          onPageChange={handlePageChange}
        />
      </main>
      
      {/* Footer */}
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
