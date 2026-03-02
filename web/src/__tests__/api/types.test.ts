import { describe, it, expect } from 'vitest';
import {
  DRONE_MODELS,
  HEIGHT_OPTIONS,
  DEFAULT_MAP_LAYERS,
} from '../../api/types';
import type {
  PointQuery,
  WindResponse,
  RiskResponse,
  RiskLevel,
  GridCell,
  Corridor,
  FAIData,
  DashboardStats,
  WindRoseSector,
  TestCase,
  TestSuite,
  TestResults,
  CoverageModule,
} from '../../api/types';

describe('PointQuery type', () => {
  it('should accept a valid point query', () => {
    const query: PointQuery = {
      lon: 121.55,
      lat: 25.03,
      height: 50,
      drone_id: 'dji-mini4-pro',
    };
    expect(query.lon).toBe(121.55);
    expect(query.lat).toBe(25.03);
    expect(query.height).toBe(50);
    expect(query.drone_id).toBe('dji-mini4-pro');
  });

  it('should accept a minimal point query without optional fields', () => {
    const query: PointQuery = { lon: 121.55, lat: 25.03 };
    expect(query.height).toBeUndefined();
    expect(query.drone_id).toBeUndefined();
  });
});

describe('WindResponse type', () => {
  it('should represent a complete wind response', () => {
    const response: WindResponse = {
      grid_id: 'G05100806',
      wind_speed: 8.5,
      wind_direction: 'NE',
      risk_level: 'yellow',
      risk_label: '注意',
      risk_score: 35,
    };
    expect(response.grid_id).toBe('G05100806');
    expect(response.risk_level).toBe('yellow');
  });
});

describe('RiskLevel type', () => {
  it('should accept all valid risk levels', () => {
    const levels: RiskLevel[] = ['green', 'yellow', 'red', 'black'];
    expect(levels).toHaveLength(4);
    expect(levels).toContain('green');
    expect(levels).toContain('black');
  });
});

describe('RiskResponse type', () => {
  it('should represent a full risk response with flyability', () => {
    const response: RiskResponse = {
      grid_id: 'G05100806',
      risk_level: 'green',
      risk_label: '安全',
      risk_score: 15,
      wind_speed_50m: 5.2,
      wind_speed_80m: 7.1,
      wind_speed_120m: 9.8,
      fai_ne: 0.45,
      is_corridor: false,
      flyability: {
        drone_id: 'dji-mini4-pro',
        drone_name: 'DJI Mini 4 Pro',
        max_wind_speed: 10.7,
        flyable: true,
        margin: 5.5,
        recommendation: 'Safe to fly. Wind conditions are well within limits.',
      },
    };
    expect(response.flyability?.flyable).toBe(true);
    expect(response.is_corridor).toBe(false);
  });
});

describe('GridCell type', () => {
  it('should represent a grid cell with all required fields', () => {
    const cell: GridCell = {
      grid_id: 'G05100806',
      lon: 121.55,
      lat: 25.03,
      risk_level: 'green',
      risk_score: 20,
      wind_speed: 4.5,
      wind_direction: 'NE',
      is_corridor: false,
    };
    expect(cell.grid_id).toMatch(/^G/);
    expect(cell.risk_level).toBe('green');
  });
});

describe('Corridor type', () => {
  it('should represent a corridor with GeoJSON geometry', () => {
    const corridor: Corridor = {
      corridor_id: 'C001',
      name: 'Keelung River Corridor',
      type: 'primary',
      geometry: {
        type: 'LineString',
        coordinates: [
          [121.54, 25.06],
          [121.56, 25.04],
        ],
      },
      mean_wind_speed: 8.5,
      dominant_direction: 'NE',
      risk_level: 'yellow',
    };
    expect(corridor.type).toBe('primary');
    expect(corridor.geometry.type).toBe('LineString');
  });
});

describe('DRONE_MODELS', () => {
  it('should contain 5 drone models', () => {
    expect(DRONE_MODELS).toHaveLength(5);
  });

  it('should contain DJI Mini 4 Pro as first model', () => {
    expect(DRONE_MODELS[0].name).toBe('DJI Mini 4 Pro');
    expect(DRONE_MODELS[0].max_wind_speed).toBe(10.7);
  });

  it('should contain DJI Matrice 350 RTK', () => {
    const matrice350 = DRONE_MODELS.find((d) => d.id === 'dji-matrice350');
    expect(matrice350).toBeDefined();
    expect(matrice350!.max_wind_speed).toBe(15.0);
    expect(matrice350!.category).toBe('enterprise');
  });

  it('should have unique IDs', () => {
    const ids = DRONE_MODELS.map((d) => d.id);
    const uniqueIds = new Set(ids);
    expect(uniqueIds.size).toBe(ids.length);
  });
});

describe('HEIGHT_OPTIONS', () => {
  it('should contain 50, 80, 120', () => {
    expect(HEIGHT_OPTIONS).toEqual([50, 80, 120]);
  });
});

describe('DEFAULT_MAP_LAYERS', () => {
  it('should have risk and corridors enabled by default', () => {
    expect(DEFAULT_MAP_LAYERS.risk).toBe(true);
    expect(DEFAULT_MAP_LAYERS.corridors).toBe(true);
  });

  it('should have fai and wind_arrows disabled by default', () => {
    expect(DEFAULT_MAP_LAYERS.fai).toBe(false);
    expect(DEFAULT_MAP_LAYERS.wind_arrows).toBe(false);
  });
});

describe('DashboardStats type', () => {
  it('should have required fields', () => {
    const stats: DashboardStats = {
      total_grids: 1500,
      risk_distribution: { green: 800, yellow: 400, red: 200, black: 100 },
      corridor_count: 12,
      mean_wind_speed: 7.3,
      monitoring_area_km2: 45.2,
      last_updated: '2024-03-01T12:00:00Z',
    };
    expect(stats.total_grids).toBe(1500);
    expect(Object.keys(stats.risk_distribution)).toHaveLength(4);
  });
});

describe('WindRoseSector type', () => {
  it('should represent wind rose data', () => {
    const sector: WindRoseSector = {
      direction: 'NE',
      angle: 45,
      frequency: 0.25,
      mean_speed: 8.5,
    };
    expect(sector.direction).toBe('NE');
    expect(sector.frequency).toBeLessThanOrEqual(1);
  });
});

describe('FAIData type', () => {
  it('should represent FAI values', () => {
    const fai: FAIData = {
      grid_id: 'G05100806',
      fai_value: 0.85,
      lon: 121.55,
      lat: 25.03,
      terrain_roughness: 1.2,
      building_density: 0.65,
    };
    expect(fai.fai_value).toBeGreaterThanOrEqual(0);
  });
});

describe('Test result types', () => {
  it('should represent a test case', () => {
    const tc: TestCase = {
      name: 'test_wind_query',
      status: 'passed',
      duration: 120,
    };
    expect(tc.status).toBe('passed');
  });

  it('should represent a test suite', () => {
    const suite: TestSuite = {
      name: 'test_api',
      framework: 'pytest',
      tests: [],
      passed: 10,
      failed: 0,
      skipped: 1,
      duration: 2500,
    };
    expect(suite.framework).toBe('pytest');
  });

  it('should represent full test results with coverage', () => {
    const mod: CoverageModule = {
      name: 'api/wind',
      statements: 85,
      branches: 72,
      functions: 90,
      lines: 87,
      percentage: 83.5,
    };

    const results: TestResults = {
      suites: [],
      total_passed: 50,
      total_failed: 2,
      total_skipped: 3,
      total_duration: 15000,
      coverage: [mod],
      last_run: '2024-03-01T12:00:00Z',
    };
    expect(results.total_passed + results.total_failed + results.total_skipped).toBe(55);
    expect(results.coverage).toHaveLength(1);
  });
});
