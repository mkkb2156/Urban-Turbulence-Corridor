import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  toFixed,
  formatWindSpeed,
  formatRiskScore,
  formatPercentage,
  formatLon,
  formatLat,
  formatCoords,
  formatHeight,
  formatDateTime,
  formatDuration,
  formatRelativeTime,
  abbreviateNumber,
} from '../../utils/format';

describe('toFixed', () => {
  it('should format number to 2 decimal places by default', () => {
    expect(toFixed(3.14159)).toBe('3.14');
  });

  it('should format number to specified decimal places', () => {
    expect(toFixed(3.14159, 3)).toBe('3.142');
    expect(toFixed(3.14159, 0)).toBe('3');
  });

  it('should pad with zeros', () => {
    expect(toFixed(5, 2)).toBe('5.00');
  });
});

describe('formatWindSpeed', () => {
  it('should format wind speed with m/s unit', () => {
    expect(formatWindSpeed(5.67)).toBe('5.7 m/s');
    expect(formatWindSpeed(10)).toBe('10.0 m/s');
    expect(formatWindSpeed(0)).toBe('0.0 m/s');
  });
});

describe('formatRiskScore', () => {
  it('should format risk score as rounded percentage', () => {
    expect(formatRiskScore(75.4)).toBe('75%');
    expect(formatRiskScore(0)).toBe('0%');
    expect(formatRiskScore(100)).toBe('100%');
  });
});

describe('formatPercentage', () => {
  it('should format percentage with one decimal place by default', () => {
    expect(formatPercentage(85.67)).toBe('85.7%');
  });

  it('should support custom decimal places', () => {
    expect(formatPercentage(85.67, 0)).toBe('86%');
    expect(formatPercentage(85.67, 2)).toBe('85.67%');
  });
});

describe('formatLon', () => {
  it('should format positive longitude as East', () => {
    expect(formatLon(121.55)).toBe('121.5500\u00B0 E');
  });

  it('should format negative longitude as West', () => {
    expect(formatLon(-122.45)).toBe('122.4500\u00B0 W');
  });
});

describe('formatLat', () => {
  it('should format positive latitude as North', () => {
    expect(formatLat(25.03)).toBe('25.0300\u00B0 N');
  });

  it('should format negative latitude as South', () => {
    expect(formatLat(-33.87)).toBe('33.8700\u00B0 S');
  });
});

describe('formatCoords', () => {
  it('should format lon/lat as lat, lon string', () => {
    const result = formatCoords(121.55, 25.03);
    expect(result).toContain('25.0300');
    expect(result).toContain('121.5500');
    expect(result).toContain('N');
    expect(result).toContain('E');
  });
});

describe('formatHeight', () => {
  it('should format height with AGL unit', () => {
    expect(formatHeight(50)).toBe('50m AGL');
    expect(formatHeight(120)).toBe('120m AGL');
  });
});

describe('formatDateTime', () => {
  it('should format ISO string to localized date-time', () => {
    const result = formatDateTime('2024-03-01T12:30:00Z');
    // This will vary by locale, but should at least contain year and time parts
    expect(result).toBeTruthy();
    expect(typeof result).toBe('string');
  });
});

describe('formatDuration', () => {
  it('should format milliseconds', () => {
    expect(formatDuration(500)).toBe('500ms');
  });

  it('should format seconds', () => {
    expect(formatDuration(3500)).toBe('3.5s');
  });

  it('should format minutes and seconds', () => {
    expect(formatDuration(125000)).toBe('2m 5s');
  });
});

describe('formatRelativeTime', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2024-03-01T12:00:00Z'));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should return "just now" for recent timestamps', () => {
    expect(formatRelativeTime('2024-03-01T11:59:30Z')).toBe('just now');
  });

  it('should return minutes ago', () => {
    expect(formatRelativeTime('2024-03-01T11:55:00Z')).toBe('5 minutes ago');
  });

  it('should return hours ago', () => {
    expect(formatRelativeTime('2024-03-01T09:00:00Z')).toBe('3 hours ago');
  });

  it('should return days ago', () => {
    expect(formatRelativeTime('2024-02-28T12:00:00Z')).toBe('2 days ago');
  });

  it('should handle singular forms', () => {
    expect(formatRelativeTime('2024-03-01T11:59:00Z')).toBe('1 minute ago');
    expect(formatRelativeTime('2024-03-01T11:00:00Z')).toBe('1 hour ago');
    expect(formatRelativeTime('2024-02-29T12:00:00Z')).toBe('1 day ago');
  });
});

describe('abbreviateNumber', () => {
  it('should not abbreviate numbers below 1000', () => {
    expect(abbreviateNumber(999)).toBe('999');
    expect(abbreviateNumber(0)).toBe('0');
  });

  it('should abbreviate thousands with K', () => {
    expect(abbreviateNumber(1200)).toBe('1.2K');
    expect(abbreviateNumber(50000)).toBe('50.0K');
  });

  it('should abbreviate millions with M', () => {
    expect(abbreviateNumber(1500000)).toBe('1.5M');
  });
});
