// ─── Taiwan Coordinate Bounds ──────────────────────────────────
export const TAIWAN_BOUNDS = {
  minLon: 119.0,
  maxLon: 123.0,
  minLat: 21.0,
  maxLat: 26.0,
} as const;

// ─── Default Map Center (Taipei Xinyi District) ────────────────
export const DEFAULT_CENTER: [number, number] = [121.55, 25.03];
export const DEFAULT_ZOOM = 13;

// ─── Coordinate Validation ─────────────────────────────────────

/**
 * Check whether a longitude value falls within Taiwan's range.
 */
export function isValidTaiwanLon(lon: number): boolean {
  return lon >= TAIWAN_BOUNDS.minLon && lon <= TAIWAN_BOUNDS.maxLon;
}

/**
 * Check whether a latitude value falls within Taiwan's range.
 */
export function isValidTaiwanLat(lat: number): boolean {
  return lat >= TAIWAN_BOUNDS.minLat && lat <= TAIWAN_BOUNDS.maxLat;
}

/**
 * Check whether a lon/lat pair falls within Taiwan's bounding box.
 */
export function isInTaiwan(lon: number, lat: number): boolean {
  return isValidTaiwanLon(lon) && isValidTaiwanLat(lat);
}

// ─── Distance Calculation ──────────────────────────────────────

/**
 * Calculate the Haversine distance between two points in meters.
 */
export function haversineDistance(
  lon1: number,
  lat1: number,
  lon2: number,
  lat2: number,
): number {
  const R = 6371000; // Earth's radius in meters
  const toRad = (deg: number) => (deg * Math.PI) / 180;

  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

  return R * c;
}

// ─── Grid ID Encoding/Decoding ─────────────────────────────────

/**
 * Encode a lon/lat pair into a grid ID string.
 * Grid IDs use 0.005 degree resolution (roughly 500m).
 */
export function encodeGridId(lon: number, lat: number): string {
  const lonIdx = Math.floor((lon - TAIWAN_BOUNDS.minLon) / 0.005);
  const latIdx = Math.floor((lat - TAIWAN_BOUNDS.minLat) / 0.005);
  return `G${String(lonIdx).padStart(4, '0')}${String(latIdx).padStart(4, '0')}`;
}

/**
 * Decode a grid ID string back to the grid cell's center lon/lat.
 */
export function decodeGridId(gridId: string): { lon: number; lat: number } | null {
  const match = /^G(\d{4})(\d{4})$/.exec(gridId);
  if (!match) return null;

  const lonIdx = parseInt(match[1], 10);
  const latIdx = parseInt(match[2], 10);

  return {
    lon: TAIWAN_BOUNDS.minLon + lonIdx * 0.005 + 0.0025,
    lat: TAIWAN_BOUNDS.minLat + latIdx * 0.005 + 0.0025,
  };
}

// ─── Grid Cell Polygon ─────────────────────────────────────────

/**
 * Generate the four corners of a grid cell polygon for a given center point.
 * Returns coordinates in GeoJSON order: [lon, lat].
 */
export function gridCellPolygon(
  lon: number,
  lat: number,
  resolution = 0.005,
): [number, number][] {
  const halfRes = resolution / 2;
  return [
    [lon - halfRes, lat - halfRes],
    [lon + halfRes, lat - halfRes],
    [lon + halfRes, lat + halfRes],
    [lon - halfRes, lat + halfRes],
    [lon - halfRes, lat - halfRes], // close the polygon
  ];
}

// ─── Wind Direction ────────────────────────────────────────────

const DIRECTION_NAMES = [
  'N', 'NNE', 'NE', 'ENE',
  'E', 'ESE', 'SE', 'SSE',
  'S', 'SSW', 'SW', 'WSW',
  'W', 'WNW', 'NW', 'NNW',
] as const;

/**
 * Convert a wind direction in degrees to a 16-sector compass label.
 */
export function degreesToDirection(degrees: number): string {
  const normalized = ((degrees % 360) + 360) % 360;
  const index = Math.round(normalized / 22.5) % 16;
  return DIRECTION_NAMES[index];
}

/**
 * Convert a 16-sector compass label to degrees.
 */
export function directionToDegrees(direction: string): number | null {
  const index = DIRECTION_NAMES.indexOf(
    direction.toUpperCase() as (typeof DIRECTION_NAMES)[number],
  );
  if (index === -1) return null;
  return index * 22.5;
}

// ─── Bearing Calculation ───────────────────────────────────────

/**
 * Calculate the initial bearing from point A to point B in degrees.
 */
export function bearing(
  lon1: number,
  lat1: number,
  lon2: number,
  lat2: number,
): number {
  const toRad = (deg: number) => (deg * Math.PI) / 180;
  const toDeg = (rad: number) => (rad * 180) / Math.PI;

  const dLon = toRad(lon2 - lon1);
  const y = Math.sin(dLon) * Math.cos(toRad(lat2));
  const x =
    Math.cos(toRad(lat1)) * Math.sin(toRad(lat2)) -
    Math.sin(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.cos(dLon);
  const brng = toDeg(Math.atan2(y, x));
  return (brng + 360) % 360;
}
