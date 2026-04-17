import { useState } from 'react';
import { Plane, RefreshCw, Activity, DatabaseZap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { 
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue 
} from '@/components/ui/select';
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter
} from '@/components/ui/dialog';
import { useHealthCheck } from '@/hooks/useStatistics';
import { flightsApi } from '@/api/client';
import { toast } from 'sonner';

interface HeaderProps {
  onRefresh: () => void;
  loading?: boolean;
}

export function Header({ onRefresh, loading }: HeaderProps) {
  const { healthy, loading: healthLoading } = useHealthCheck();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // حالة نموذج الجلب التاريخي
  const [historicalData, setHistoricalData] = useState({
    start_date: '',
    end_date: '',
    region: 'all'
  });

  const handleRefresh = () => {
    onRefresh();
    toast.info('Refreshing data...');
  };

  const handleHistoricalSubmit = async () => {
    if (!historicalData.start_date || !historicalData.end_date) {
      toast.error('Please select both start and end dates.');
      return;
    }

    try {
      setIsSubmitting(true);
      const payload = {
        start_date: historicalData.start_date,
        end_date: historicalData.end_date,
        region: historicalData.region === 'all' ? null : historicalData.region
      };
      
      await flightsApi.ingestHistorical(payload);
      toast.success('Historical ingestion started in the background! This may take a while.');
      setIsModalOpen(false); // إغلاق النافذة بعد النجاح
    } catch (error) {
      toast.error('Failed to start historical ingestion.');
      console.error(error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="bg-primary p-2 rounded-lg">
              <Plane className="h-6 w-6 text-primary-foreground" />
            </div>
            <div>
              <h1 className="text-xl font-bold">Flight Intelligence</h1>
              <p className="text-xs text-muted-foreground">Real-time Flight Tracking & Analytics</p>
            </div>
          </div>

          {/* Status & Actions */}
          <div className="flex items-center gap-3">
            {!healthLoading && (
              <Badge 
                variant={healthy ? "default" : "destructive"}
                className="hidden sm:flex items-center gap-1"
              >
                <Activity className="h-3 w-3" />
                {healthy ? 'System Online' : 'System Offline'}
              </Badge>
            )}

            {/* زر الجلب التاريخي مع النافذة المنبثقة */}
            <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
              <DialogTrigger asChild>
                <Button variant="secondary" size="sm">
                  <DatabaseZap className="h-4 w-4 mr-2" />
                  Historical Data
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                  <DialogTitle>Fetch Historical Data</DialogTitle>
                  <DialogDescription>
                    Select a date range and region to fetch historical flight data. This process will run in the background.
                  </DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  <div className="grid gap-2">
                    <Label htmlFor="start_date">Start Date</Label>
                    <Input 
                      id="start_date" 
                      type="date" 
                      value={historicalData.start_date}
                      onChange={(e) => setHistoricalData({...historicalData, start_date: e.target.value})}
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="end_date">End Date</Label>
                    <Input 
                      id="end_date" 
                      type="date" 
                      value={historicalData.end_date}
                      onChange={(e) => setHistoricalData({...historicalData, end_date: e.target.value})}
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="region">Region</Label>
                    <Select 
                      value={historicalData.region} 
                      onValueChange={(val) => setHistoricalData({...historicalData, region: val})}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select a region" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">Global (All Regions)</SelectItem>
                        <SelectItem value="middle_east">Middle East</SelectItem>
                        <SelectItem value="north_africa">North Africa</SelectItem>
                        <SelectItem value="central_asia">Central Asia</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setIsModalOpen(false)}>Cancel</Button>
                  <Button onClick={handleHistoricalSubmit} disabled={isSubmitting}>
                    {isSubmitting ? 'Starting...' : 'Start Ingestion'}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>

            {/* Refresh Button */}
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handleRefresh}
              disabled={loading}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </div>
      </div>
    </header>
  );
}