import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from './client';
import type {
  PointQuery,
  WindResponse,
  RiskResponse,
  DashboardStats,
  GridCell,
  Corridor,
  FAIData,
  WindRoseSector,
  TestResults,
  HeightOption,
  ForecastResponse,
  CWAStationsResponse,
  AreaPredictRequest,
  AreaPredictResponse,
  RouteAnalyzeResponse,
  RoutePlanResponse,
  MonitorResponse,
  BatchPointQuery,
  BatchRiskResponse,
} from './types';

// ─── Query Keys ────────────────────────────────────────────────
export const queryKeys = {
  wind: (q: PointQuery) => ['wind', q] as const,
  risk: (q: PointQuery) => ['risk', q] as const,
  stats: () => ['stats'] as const,
  grids: (height: HeightOption) => ['grids', height] as const,
  corridors: () => ['corridors'] as const,
  fai: (height: HeightOption) => ['fai', height] as const,
  windRose: () => ['wind-rose'] as const,
  testResults: () => ['test-results'] as const,
  monitor: () => ['monitor'] as const,
  forecast: (city: string, hours: number) => ['forecast', city, hours] as const,
  cwaStations: (region: string) => ['cwa-stations', region] as const,
};

// ─── Wind Query ────────────────────────────────────────────────
export function useWindQuery(query: PointQuery, enabled = true) {
  return useQuery({
    queryKey: queryKeys.wind(query),
    queryFn: () =>
      apiClient.get<WindResponse>('/wind', {
        lon: query.lon,
        lat: query.lat,
        height: query.height,
        drone_id: query.drone_id,
      }),
    enabled,
  });
}

// ─── Risk Query ────────────────────────────────────────────────
export function useRiskQuery(query: PointQuery, enabled = true) {
  return useQuery({
    queryKey: queryKeys.risk(query),
    queryFn: () =>
      apiClient.get<RiskResponse>('/risk', {
        lon: query.lon,
        lat: query.lat,
        height: query.height,
        drone_id: query.drone_id,
      }),
    enabled,
  });
}

// ─── Dashboard Stats ───────────────────────────────────────────
export function useDashboardStats() {
  return useQuery({
    queryKey: queryKeys.stats(),
    queryFn: () => apiClient.get<DashboardStats>('/stats'),
  });
}

// ─── Grid Cells ────────────────────────────────────────────────
export function useGridCells(height: HeightOption) {
  return useQuery({
    queryKey: queryKeys.grids(height),
    queryFn: () => apiClient.get<GridCell[]>('/grids', { height }),
    staleTime: 10 * 60 * 1000, // 10 minutes - grid data changes infrequently
  });
}

// ─── Corridors ─────────────────────────────────────────────────
export function useCorridors() {
  return useQuery({
    queryKey: queryKeys.corridors(),
    queryFn: () => apiClient.get<Corridor[]>('/corridors'),
    staleTime: 30 * 60 * 1000, // 30 minutes
  });
}

// ─── FAI Data ──────────────────────────────────────────────────
export function useFAIData(height: HeightOption) {
  return useQuery({
    queryKey: queryKeys.fai(height),
    queryFn: () => apiClient.get<FAIData[]>('/fai', { height }),
    staleTime: 10 * 60 * 1000,
  });
}

// ─── Wind Rose ─────────────────────────────────────────────────
export function useWindRose() {
  return useQuery({
    queryKey: queryKeys.windRose(),
    queryFn: () => apiClient.get<WindRoseSector[]>('/wind-rose'),
  });
}

// ─── Test Results ──────────────────────────────────────────────
export function useTestResults() {
  return useQuery({
    queryKey: queryKeys.testResults(),
    queryFn: () => apiClient.get<TestResults>('/test-results'),
    staleTime: 30 * 1000, // 30 seconds - tests might rerun
  });
}

// ─── Monitor ─────────────────────────────────────────────────
export function useMonitor() {
  return useQuery({
    queryKey: queryKeys.monitor(),
    queryFn: () => apiClient.get<MonitorResponse>('/monitor'),
    staleTime: 30 * 1000,
    refetchInterval: 30 * 1000,
  });
}

// ─── Trigger Test Run ──────────────────────────────────────────
export function useTriggerTests() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => apiClient.post<{ status: string }>('/test-results/run'),
    onSuccess: () => {
      // Invalidate and refetch test results after triggering
      queryClient.invalidateQueries({ queryKey: queryKeys.testResults() });
    },
  });
}

// ─── Flyability Check ──────────────────────────────────────────
export function useFlyabilityCheck() {
  return useMutation({
    mutationFn: (query: PointQuery) =>
      apiClient.get<RiskResponse>('/risk', {
        lon: query.lon,
        lat: query.lat,
        height: query.height,
        drone_id: query.drone_id,
      }),
  });
}

// ─── Forecast ─────────────────────────────────────────────────
export function useForecast(city = 'taipei', hours = 72) {
  return useQuery({
    queryKey: queryKeys.forecast(city, hours),
    queryFn: () => apiClient.get<ForecastResponse>('/forecast', { city, hours }),
    staleTime: 5 * 60 * 1000,
  });
}

// ─── CWA Stations ─────────────────────────────────────────────
export function useCWAStations(region = 'taipei') {
  return useQuery({
    queryKey: queryKeys.cwaStations(region),
    queryFn: () => apiClient.get<CWAStationsResponse>('/forecast/stations', { region }),
    staleTime: 5 * 60 * 1000, // 5 min — CWA updates every 10 min
    retry: 1,
  });
}

// ─── Area Prediction ──────────────────────────────────────────
export function useAreaPrediction() {
  return useMutation({
    mutationFn: (req: AreaPredictRequest) =>
      apiClient.post<AreaPredictResponse>('/area/predict', req),
  });
}

// ─── Route Analysis ───────────────────────────────────────────
export function useRouteAnalysis() {
  return useMutation({
    mutationFn: (req: { waypoints: [number, number][]; height?: number; drone_id?: string }) =>
      apiClient.post<RouteAnalyzeResponse>('/route/analyze', req),
  });
}

// ─── Batch Risk Check ─────────────────────────────────────────
export function useBatchRiskCheck() {
  return useMutation({
    mutationFn: (req: BatchPointQuery) =>
      apiClient.post<BatchRiskResponse>('/risk/batch', req),
  });
}

// ─── Route Planning ───────────────────────────────────────────
export function useRoutePlan() {
  return useMutation({
    mutationFn: (req: { start: [number, number]; end: [number, number]; height?: number; drone_id?: string; mode?: string }) =>
      apiClient.post<RoutePlanResponse>('/route/plan', req),
  });
}
