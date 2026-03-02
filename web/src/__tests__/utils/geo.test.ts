import { describe, it, expect } from 'vitest';
import {
  TAIWAN_BOUNDS,
  DEFAULT_CENTER,
  DEFAULT_ZOOM,
  isValidTaiwanLon,
  isValidTaiwanLat,
  isInTaiwan,
  haversineDistance,
  encodeGridId,
  decodeGridId,
  gridCellPolygon,
  degreesToDirection,
  directionToDegrees,
  bearing,
} from '../../utils/geo';

describe('TAIWAN_BOUNDS', () => {
  it('should define valid bounding box for Taiwan', () => {
    expect(TAIWAN_BOUNDS.minLon).toBe(119);
    expect(TAIWAN_BOUNDS.maxLon).toBe(123);
    expect(TAIWAN_BOUNDS.minLat).toBe(21);
    expect(TAIWAN_BOUNDS.maxLat).toBe(26);
  });
});

describe('DEFAULT_CENTER', () => {
  it('should be set to Taipei Xinyi District', () => {
    expect(DEFAULT_CENTER).toEqual([121.55, 25.03]);
  });
});

describe('DEFAULT_ZOOM', () => {
  it('should be 13', () => {
    expect(DEFAULT_ZOOM).toBe(13);
  });
});

describe('isValidTaiwanLon', () => {
  it('should return true for longitudes within Taiwan range', () => {
    expect(isValidTaiwanLon(121.55)).toBe(true);
    expect(isValidTaiwanLon(119)).toBe(true);
    expect(isValidTaiwanLon(123)).toBe(true);
  });

  it('should return false for longitudes outside Taiwan range', () => {
    expect(isValidTaiwanLon(118.99)).toBe(false);
    expect(isValidTaiwanLon(123.01)).toBe(false);
    expect(isValidTaiwanLon(0)).toBe(false);
  });
});

describe('isValidTaiwanLat', () => {
  it('should return true for latitudes within Taiwan range', () => {
    expect(isValidTaiwanLat(25.03)).toBe(true);
    expect(isValidTaiwanLat(21)).toBe(true);
    expect(isValidTaiwanLat(26)).toBe(true);
  });

  it('should return false for latitudes outside Taiwan range', () => {
    expect(isValidTaiwanLat(20.99)).toBe(false);
    expect(isValidTaiwanLat(26.01)).toBe(false);
    expect(isValidTaiwanLat(0)).toBe(false);
  });
});

describe('isInTaiwan', () => {
  it('should return true for coordinates within Taiwan', () => {
    expect(isInTaiwan(121.55, 25.03)).toBe(true); // Taipei
    expect(isInTaiwan(120.31, 22.62)).toBe(true); // Kaohsiung
  });

  it('should return false for coordinates outside Taiwan', () => {
    expect(isInTaiwan(139.69, 35.69)).toBe(false); // Tokyo
    expect(isInTaiwan(0, 0)).toBe(false);
  });
});

describe('haversineDistance', () => {
  it('should return 0 for identical points', () => {
    expect(haversineDistance(121.55, 25.03, 121.55, 25.03)).toBe(0);
  });

  it('should calculate distance between Taipei and Kaohsiung (~300km)', () => {
    const distance = haversineDistance(121.55, 25.03, 120.31, 22.62);
    // Taipei to Kaohsiung is roughly 300-350 km
    expect(distance).toBeGreaterThan(280_000);
    expect(distance).toBeLessThan(360_000);
  });

  it('should be symmetric', () => {
    const d1 = haversineDistance(121.55, 25.03, 120.31, 22.62);
    const d2 = haversineDistance(120.31, 22.62, 121.55, 25.03);
    expect(d1).toBeCloseTo(d2, 5);
  });
});

describe('encodeGridId', () => {
  it('should encode coordinates to a grid ID string', () => {
    const gridId = encodeGridId(121.55, 25.03);
    expect(gridId).toMatch(/^G\d{4}\d{4}$/);
  });

  it('should encode the minimum bounds correctly', () => {
    const gridId = encodeGridId(119.0, 21.0);
    expect(gridId).toBe('G00000000');
  });
});

describe('decodeGridId', () => {
  it('should decode a valid grid ID to coordinates', () => {
    const result = decodeGridId('G00000000');
    expect(result).not.toBeNull();
    expect(result!.lon).toBeCloseTo(119.0025, 4);
    expect(result!.lat).toBeCloseTo(21.0025, 4);
  });

  it('should return null for invalid grid ID', () => {
    expect(decodeGridId('invalid')).toBeNull();
    expect(decodeGridId('G123')).toBeNull();
    expect(decodeGridId('')).toBeNull();
  });

  it('should roundtrip encode/decode approximately', () => {
    const lon = 121.55;
    const lat = 25.03;
    const gridId = encodeGridId(lon, lat);
    const decoded = decodeGridId(gridId);
    expect(decoded).not.toBeNull();
    // Should be within half a grid cell (0.0025 degrees)
    expect(Math.abs(decoded!.lon - lon)).toBeLessThan(0.005);
    expect(Math.abs(decoded!.lat - lat)).toBeLessThan(0.005);
  });
});

describe('gridCellPolygon', () => {
  it('should return 5 coordinate pairs (closed polygon)', () => {
    const polygon = gridCellPolygon(121.55, 25.03);
    expect(polygon).toHaveLength(5);
  });

  it('should close the polygon (first and last point are the same)', () => {
    const polygon = gridCellPolygon(121.55, 25.03);
    expect(polygon[0]).toEqual(polygon[4]);
  });

  it('should create a square centered on the given point', () => {
    const polygon = gridCellPolygon(121.55, 25.03, 0.01);
    const [sw, se, ne, nw] = polygon;
    // Southwest corner
    expect(sw[0]).toBeCloseTo(121.545, 4);
    expect(sw[1]).toBeCloseTo(25.025, 4);
    // Northeast corner
    expect(ne[0]).toBeCloseTo(121.555, 4);
    expect(ne[1]).toBeCloseTo(25.035, 4);
  });
});

describe('degreesToDirection', () => {
  it('should convert 0 degrees to N', () => {
    expect(degreesToDirection(0)).toBe('N');
  });

  it('should convert 90 degrees to E', () => {
    expect(degreesToDirection(90)).toBe('E');
  });

  it('should convert 180 degrees to S', () => {
    expect(degreesToDirection(180)).toBe('S');
  });

  it('should convert 270 degrees to W', () => {
    expect(degreesToDirection(270)).toBe('W');
  });

  it('should convert 45 degrees to NE', () => {
    expect(degreesToDirection(45)).toBe('NE');
  });

  it('should handle negative degrees', () => {
    expect(degreesToDirection(-90)).toBe('W');
  });

  it('should handle degrees > 360', () => {
    expect(degreesToDirection(450)).toBe('E');
  });
});

describe('directionToDegrees', () => {
  it('should convert N to 0', () => {
    expect(directionToDegrees('N')).toBe(0);
  });

  it('should convert NE to 45', () => {
    expect(directionToDegrees('NE')).toBe(45);
  });

  it('should convert E to 90', () => {
    expect(directionToDegrees('E')).toBe(90);
  });

  it('should return null for invalid direction', () => {
    expect(directionToDegrees('INVALID')).toBeNull();
    expect(directionToDegrees('')).toBeNull();
  });

  it('should be case-insensitive', () => {
    expect(directionToDegrees('ne')).toBe(45);
    expect(directionToDegrees('nE')).toBe(45);
  });
});

describe('bearing', () => {
  it('should calculate bearing from south to north as approximately 0', () => {
    const b = bearing(121.55, 25.0, 121.55, 25.5);
    expect(b).toBeCloseTo(0, 0);
  });

  it('should calculate bearing east as approximately 90', () => {
    const b = bearing(121.0, 25.0, 121.5, 25.0);
    expect(b).toBeCloseTo(90, 0);
  });

  it('should calculate bearing south as approximately 180', () => {
    const b = bearing(121.55, 25.5, 121.55, 25.0);
    expect(b).toBeCloseTo(180, 0);
  });
});
