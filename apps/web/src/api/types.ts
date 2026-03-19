// ─── 基本型別 ────────────────────────────────────────────────

export type RiskLevel = "green" | "yellow" | "red" | "black";

export interface PointQuery {
  lon: number;
  lat: number;
  height?: number;
  drone_id?: string;
}

// ─── 機型 ─────────────────────────────────────────────────────

export interface DroneModel {
  id: string;
  name: string;
  max_wind_speed: number;
  safe_limit: number;
  weight_kg: number;
  category: "consumer" | "prosumer" | "enterprise";
}

export const DRONE_MODELS: DroneModel[] = [
  { id: "dji-mini4-pro", name: "DJI Mini 4 Pro", max_wind_speed: 10.7, safe_limit: 7.5, weight_kg: 0.249, category: "consumer" },
  { id: "dji-air3", name: "DJI Air 3", max_wind_speed: 12.0, safe_limit: 8.4, weight_kg: 0.72, category: "consumer" },
  { id: "dji-mavic3", name: "DJI Mavic 3 Enterprise", max_wind_speed: 12.0, safe_limit: 8.4, weight_kg: 0.895, category: "prosumer" },
  { id: "dji-matrice30", name: "DJI Matrice 30T", max_wind_speed: 15.0, safe_limit: 10.5, weight_kg: 3.77, category: "enterprise" },
  { id: "dji-matrice350", name: "DJI Matrice 350 RTK", max_wind_speed: 15.0, safe_limit: 10.5, weight_kg: 6.47, category: "enterprise" },
  { id: "dji-matrice400", name: "DJI Matrice 400", max_wind_speed: 15.0, safe_limit: 10.5, weight_kg: 7.0, category: "enterprise" },
];

// ─── Flight Summary (v4 新增) ─────────────────────────────────

export interface FlightWindow {
  start: string;
  end: string;
  risk: RiskLevel;
}

export interface FlightSummary {
  risk_level: RiskLevel;
  risk_score: number;
  wind_speed: number;
  wind_gust: number;
  wind_direction_label: string;
  drone_ok: boolean;
  drone_safe_limit: number;
  battery_extra_pct: number;
  in_corridor: boolean;
  corridor_warning: string | null;
  best_windows: FlightWindow[];
  worst_period: FlightWindow | null;
  generated_at: string;
}

// ─── Wind Texture (v4 新增) ───────────────────────────────────

export interface WindTextureMetadata {
  bounds: [number, number, number, number];
  windMin: number;
  windMax: number;
  width: number;
  height: number;
}

// ─── Corridor ─────────────────────────────────────────────────

export interface Corridor {
  corridor_id: string;
  name: string;
  type: "primary" | "secondary";
  geometry: GeoJSON.LineString;
  mean_wind_speed: number;
  dominant_direction: string;
  risk_level: RiskLevel;
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
  source: string;
  forecasts: ForecastPoint[];
}

// ─── 地圖圖層控制 ────────────────────────────────────────────

export interface MapLayerVisibility {
  riskGrid: boolean;
  corridors: boolean;
  windField: boolean;
  buildings3d: boolean;
  airspace: boolean;
  morphology: boolean;
}

export const DEFAULT_LAYER_VISIBILITY: MapLayerVisibility = {
  riskGrid: true,
  corridors: true,
  windField: true,
  buildings3d: false,
  airspace: true,
  morphology: false,
};
