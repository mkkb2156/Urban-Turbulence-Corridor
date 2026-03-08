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
  turbulence?: number | null;
  gust_factor?: number | null;
  shelter_index?: number | null;
  lcz_class?: number | null;
  lcz_label?: string | null;
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
  wind_direction_deg?: number | null;
}

export interface CorridorComputeRequest {
  city?: string;
  wind_direction: number;
  n_corridors?: number;
  fai_col?: string | null;
  multi_direction?: boolean;
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
  wind_speed_80m?: number | null;
  wind_direction_80m?: number | null;
  wind_speed_120m?: number | null;
  wind_direction_120m?: number | null;
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
  crosswind: number;
  wind_effect_pct: number;
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

// ─── Monitor ─────────────────────────────────────────────────
export interface MonitorService {
  name: string;
  status: 'up' | 'down';
  latency_ms: number;
  details: Record<string, unknown>;
  error?: string | null;
}

export interface MonitorResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  version: string;
  services: MonitorService[];
}

// ─── Batch Risk Query ─────────────────────────────────────────
export interface BatchPointQuery {
  points: { lon: number; lat: number; height?: number; drone_id?: string }[];
}

export interface BatchRiskResult {
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

export interface BatchRiskResponse {
  results: BatchRiskResult[];
  total: number;
  flyable_count: number;
  not_flyable_count: number;
}

// ─── Regional Wind ────────────────────────────────────────────
export interface RegionalWindPoint {
  lon: number;
  lat: number;
  wind_speed: number;
  wind_direction: number;
  wind_gusts: number;
  u: number;
  v: number;
  risk_level: RiskLevel;
}

export interface RegionalWindResponse {
  bbox: [number, number, number, number];
  grid: { n_lon: number; n_lat: number; resolution: number };
  height_m: number;
  points: RegionalWindPoint[];
  point_count: number;
  source: 'open-meteo' | 'mock';
  generated_at: string;
}

// ─── Drone Power ──────────────────────────────────────────────
export interface DronePowerRequest {
  drone_id: string;
  wind_speed: number;
  wind_angle?: number;
  cruise_speed?: number | null;
  altitude?: number;
}

export interface DronePowerResponse {
  drone_id: string;
  drone_name: string;
  hover_power_w: number;
  forward_power_w: number;
  groundspeed_ms: number;
  endurance_min: number;
  range_km: number;
  battery_impact_pct: number;
  headwind_ms: number;
  crosswind_ms: number;
  battery_capacity_wh: number;
  generated_at: string;
}

export interface MissionFeasibilityRequest {
  drone_id: string;
  waypoints: [number, number][];
  height?: number;
  reserve_pct?: number;
}

export interface MissionFeasibilityResponse {
  drone_id: string;
  drone_name: string;
  feasible: boolean;
  total_energy_wh: number;
  battery_capacity_wh: number;
  battery_remaining_pct: number;
  total_time_min: number;
  critical_segments: number;
  recommended_speed_ms: number;
  segments_detail: {
    distance_m: number;
    bearing: number;
    wind_speed: number;
    power_w: number;
    groundspeed_ms: number;
    travel_time_s: number;
    energy_wh: number;
    battery_impact_pct: number;
    is_critical: boolean;
  }[];
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
  particles: boolean;
  contours: boolean;
}

export const DEFAULT_MAP_LAYERS: MapLayers = {
  risk: true,
  fai: false,
  corridors: true,
  wind_arrows: false,
  particles: false,
  contours: false,
};

// ─── Derived Data (Phase 3) ──────────────────────────────────
export interface DerivedData {
  grid_id: string;
  lon: number;
  lat: number;
  morphology: {
    z0: number | null;
    zd: number | null;
    svf: number | null;
    bcr: number | null;
    mean_height: number | null;
    max_height: number | null;
    n_buildings: number | null;
    fai_ne: number | null;
    fai_sw: number | null;
    fai_max: number | null;
  };
  wind: {
    speed_50m: number | null;
    speed_80m: number | null;
    speed_120m: number | null;
    direction_deg: number | null;
  };
  derived: {
    turbulence: {
      ti_50m: number | null;
      ti_80m: number | null;
      ti_120m: number | null;
      assessment: string;
    };
    wind_shear: {
      shear_50_80: number | null;
      shear_80_120: number | null;
      assessment: string;
    };
    gust: {
      gust_factor: number | null;
      gust_speed_50m: number | null;
      gust_speed_80m: number | null;
      gust_speed_120m: number | null;
    };
    shelter: {
      shelter_index: number | null;
      assessment: string;
    };
    altitude: {
      min_safe_alt: number | null;
      max_legal_alt: number | null;
      flyable_range_m: number | null;
    };
  };
  risk: {
    level: RiskLevel;
    score: number;
    is_corridor: boolean;
  };
  generated_at: string;
}

// ─── Flight Window ──────────────────────────────────────────
export interface FlightWindow {
  start: string;
  end: string;
  hours: number;
  avg_wind: number;
  max_wind: number;
  min_wind: number;
}

export interface FlightWindowsResponse {
  lon: number;
  lat: number;
  drone_id: string;
  max_wind_tolerance: number;
  safe_wind_threshold: number;
  source: 'open-meteo' | 'mock';
  total_hours: number;
  flyable_hours: number;
  flyable_pct: number;
  windows: FlightWindow[];
  generated_at: string;
}
