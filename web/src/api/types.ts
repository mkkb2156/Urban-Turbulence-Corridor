// ─── Point Query ───────────────────────────────────────────────
export interface PointQuery {
  lon: number; // 119-123
  lat: number; // 21-26
  height?: number; // default 50
  drone_id?: string;
}

// ─── Wind Response ─────────────────────────────────────────────
export type RiskLevel = 'green' | 'yellow' | 'red' | 'black';

export interface WindResponse {
  grid_id: string;
  wind_speed: number;
  wind_direction: string;
  risk_level: RiskLevel;
  risk_label: string;
  risk_score: number;
}

// ─── Drone Flyability ──────────────────────────────────────────
export interface DroneFlyability {
  drone_id: string;
  drone_name: string;
  max_wind_speed: number;
  flyable: boolean;
  margin: number;
  recommendation: string;
}

// ─── Risk Response ─────────────────────────────────────────────
export interface RiskResponse {
  grid_id: string;
  risk_level: string;
  risk_label: string;
  risk_score: number;
  wind_speed_50m?: number;
  wind_speed_80m?: number;
  wind_speed_120m?: number;
  fai_ne?: number;
  is_corridor: boolean;
  flyability?: DroneFlyability;
}

// ─── Grid Cell (for map rendering) ────────────────────────────
export interface GridCell {
  grid_id: string;
  lon: number;
  lat: number;
  risk_level: RiskLevel;
  risk_score: number;
  wind_speed: number;
  wind_direction: string;
  is_corridor: boolean;
}

// ─── Corridor ──────────────────────────────────────────────────
export type CorridorType = 'primary' | 'secondary';

export interface Corridor {
  corridor_id: string;
  name: string;
  type: CorridorType;
  geometry: GeoJSON.LineString;
  mean_wind_speed: number;
  dominant_direction: string;
  risk_level: RiskLevel;
}

// ─── FAI Data ──────────────────────────────────────────────────
export interface FAIData {
  grid_id: string;
  fai_value: number;
  lon: number;
  lat: number;
  terrain_roughness: number;
  building_density: number;
}

// ─── Drone Model ───────────────────────────────────────────────
export interface DroneModel {
  id: string;
  name: string;
  max_wind_speed: number;
  weight_kg: number;
  category: string;
}

export const DRONE_MODELS: DroneModel[] = [
  { id: 'dji-mini4-pro', name: 'DJI Mini 4 Pro', max_wind_speed: 10.7, weight_kg: 0.249, category: 'consumer' },
  { id: 'dji-air3', name: 'DJI Air 3', max_wind_speed: 12.0, weight_kg: 0.720, category: 'consumer' },
  { id: 'dji-mavic3', name: 'DJI Mavic 3', max_wind_speed: 12.0, weight_kg: 0.895, category: 'prosumer' },
  { id: 'dji-matrice350', name: 'DJI Matrice 350 RTK', max_wind_speed: 15.0, weight_kg: 6.470, category: 'enterprise' },
  { id: 'dji-matrice30', name: 'DJI Matrice 30', max_wind_speed: 15.0, weight_kg: 3.770, category: 'enterprise' },
];

// ─── Dashboard Stats ───────────────────────────────────────────
export interface DashboardStats {
  total_grids: number;
  risk_distribution: Record<RiskLevel, number>;
  corridor_count: number;
  mean_wind_speed: number;
  monitoring_area_km2: number;
  last_updated: string;
}

// ─── Wind Rose Data ────────────────────────────────────────────
export interface WindRoseSector {
  direction: string;
  angle: number;
  frequency: number;
  mean_speed: number;
}

// ─── Test Results ──────────────────────────────────────────────
export type TestStatus = 'passed' | 'failed' | 'skipped' | 'error';

export interface TestCase {
  name: string;
  status: TestStatus;
  duration: number;
  error_message?: string;
}

export interface TestSuite {
  name: string;
  framework: 'pytest' | 'vitest';
  tests: TestCase[];
  passed: number;
  failed: number;
  skipped: number;
  duration: number;
}

export interface CoverageModule {
  name: string;
  statements: number;
  branches: number;
  functions: number;
  lines: number;
  percentage: number;
}

export interface TestResults {
  suites: TestSuite[];
  total_passed: number;
  total_failed: number;
  total_skipped: number;
  total_duration: number;
  coverage: CoverageModule[];
  last_run: string;
}

// ─── Forecast ─────────────────────────────────────────────────
export interface ForecastPoint {
  time: string;
  wind_speed: number;
  wind_direction: number;
  wind_gusts: number;
  risk_level: RiskLevel;
}

export interface ForecastResponse {
  city: string;
  hours: number;
  source: 'open-meteo' | 'mock';
  generated_at: string;
  forecasts: ForecastPoint[];
}

// ─── CWA Station ─────────────────────────────────────────────
export interface CWAStation {
  station_id: string;
  station_name: string;
  lat: number;
  lon: number;
  wind_speed: number;
  wind_direction: number | null;
  gust_speed: number | null;
  observation_time: string | null;
  risk_level: RiskLevel;
}

export interface CWAStationsResponse {
  region: string;
  source: string;
  station_count: number;
  stations: CWAStation[];
  fetched_at: string;
}

// ─── Area Prediction ──────────────────────────────────────────
export interface AreaPredictRequest {
  polygon: [number, number][];
  height?: number;
  drone_id?: string;
  start_time?: string;
  end_time?: string;
}

export interface AreaPredictResponse {
  center: { lon: number; lat: number };
  area_km2: number;
  grid_count: number;
  height: number;
  wind_stats: {
    mean_speed: number;
    max_speed: number;
    min_speed: number;
    std_speed: number;
  };
  risk_distribution: Record<RiskLevel, number>;
  wind_rose: WindRoseSector[];
  flyability: {
    drone_id: string;
    max_wind_in_area: number;
    tolerance: number;
    safe_percentage: number;
    flyable: boolean;
  } | null;
  grid_cells: {
    lon: number;
    lat: number;
    wind_speed: number;
    wind_direction: number;
    risk_level: RiskLevel;
  }[];
  generated_at: string;
}

// ─── Route Analysis ───────────────────────────────────────────
export interface RouteSegment {
  from: [number, number];
  to: [number, number];
  distance_m: number;
  bearing: number;
  avg_wind_speed: number;
  avg_wind_direction: number;
  headwind: number;
  risk_level: RiskLevel;
  travel_time_s: number;
  sample_points: {
    lon: number;
    lat: number;
    wind_speed: number;
    wind_direction: number;
    risk_level: RiskLevel;
  }[];
}

export interface RouteAnalyzeResponse {
  waypoints: [number, number][];
  height: number;
  total_distance_m: number;
  total_time_s: number;
  max_risk: RiskLevel;
  avg_wind_speed: number;
  segments: RouteSegment[];
  flyability: {
    drone_id: string;
    max_wind_on_route: number;
    tolerance: number;
    flyable: boolean;
    danger_segments: number;
  } | null;
  generated_at: string;
}

// ─── Route Planning ───────────────────────────────────────────
export type RouteMode = 'safest' | 'shortest' | 'balanced';

export interface PlannedRoute {
  mode: RouteMode;
  waypoints: [number, number][];
  geometry: GeoJSON.LineString;
  total_distance_m: number;
  total_time_s: number;
  max_risk: RiskLevel;
  avg_risk_score: number;
  segments: RouteSegment[];
  flyable?: boolean;
}

export interface RoutePlanResponse {
  start: [number, number];
  end: [number, number];
  height: number;
  routes: PlannedRoute[];
  recommended: RouteMode;
  generated_at: string;
}

// ─── Height Options ────────────────────────────────────────────
export type HeightOption = 50 | 80 | 120;

export const HEIGHT_OPTIONS: HeightOption[] = [50, 80, 120];

// ─── Map Layer Options ─────────────────────────────────────────
export interface MapLayers {
  risk: boolean;
  fai: boolean;
  corridors: boolean;
  wind_arrows: boolean;
}

export const DEFAULT_MAP_LAYERS: MapLayers = {
  risk: true,
  fai: false,
  corridors: true,
  wind_arrows: false,
};
