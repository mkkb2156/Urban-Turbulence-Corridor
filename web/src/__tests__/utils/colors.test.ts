import { describe, it, expect } from 'vitest';
import {
  RISK_COLORS,
  RISK_LABELS,
  riskLevelFromScore,
  riskColorFromScore,
  windSpeedColor,
  interpolateHexColor,
  faiColor,
  TEST_STATUS_COLORS,
} from '../../utils/colors';

describe('RISK_COLORS', () => {
  it('should have all four risk levels', () => {
    expect(RISK_COLORS).toHaveProperty('green', '#2ecc71');
    expect(RISK_COLORS).toHaveProperty('yellow', '#f1c40f');
    expect(RISK_COLORS).toHaveProperty('red', '#e74c3c');
    expect(RISK_COLORS).toHaveProperty('black', '#2c3e50');
  });
});

describe('RISK_LABELS', () => {
  it('should have Chinese and English labels for each level', () => {
    expect(RISK_LABELS.green.zh).toBe('安全');
    expect(RISK_LABELS.green.en).toBe('Safe');
    expect(RISK_LABELS.yellow.zh).toBe('注意');
    expect(RISK_LABELS.yellow.en).toBe('Caution');
    expect(RISK_LABELS.red.zh).toBe('危險');
    expect(RISK_LABELS.red.en).toBe('Danger');
    expect(RISK_LABELS.black.zh).toBe('極度危險');
    expect(RISK_LABELS.black.en).toBe('Extreme');
  });
});

describe('riskLevelFromScore', () => {
  it('should return green for scores below 25', () => {
    expect(riskLevelFromScore(0)).toBe('green');
    expect(riskLevelFromScore(10)).toBe('green');
    expect(riskLevelFromScore(24)).toBe('green');
  });

  it('should return yellow for scores 25-49', () => {
    expect(riskLevelFromScore(25)).toBe('yellow');
    expect(riskLevelFromScore(30)).toBe('yellow');
    expect(riskLevelFromScore(49)).toBe('yellow');
  });

  it('should return red for scores 50-74', () => {
    expect(riskLevelFromScore(50)).toBe('red');
    expect(riskLevelFromScore(60)).toBe('red');
    expect(riskLevelFromScore(74)).toBe('red');
  });

  it('should return black for scores 75 and above', () => {
    expect(riskLevelFromScore(75)).toBe('black');
    expect(riskLevelFromScore(90)).toBe('black');
    expect(riskLevelFromScore(100)).toBe('black');
  });
});

describe('riskColorFromScore', () => {
  it('should return the correct hex color for a given score', () => {
    expect(riskColorFromScore(10)).toBe('#2ecc71'); // green
    expect(riskColorFromScore(30)).toBe('#f1c40f'); // yellow
    expect(riskColorFromScore(60)).toBe('#e74c3c'); // red
    expect(riskColorFromScore(80)).toBe('#2c3e50'); // black
  });
});

describe('windSpeedColor', () => {
  it('should return the lowest color for speed 0', () => {
    expect(windSpeedColor(0)).toBe('#ffffb2');
  });

  it('should return the highest color for very high speed', () => {
    expect(windSpeedColor(20)).toBe('#800026');
  });

  it('should return an interpolated color for mid-range speeds', () => {
    const color = windSpeedColor(6);
    expect(color).toMatch(/^#[0-9a-f]{6}$/i);
    // At speed 6 it should be at the fd8d3c stop
    expect(color).toBe('#fd8d3c');
  });
});

describe('interpolateHexColor', () => {
  it('should return color1 when t=0', () => {
    expect(interpolateHexColor('#000000', '#ffffff', 0)).toBe('#000000');
  });

  it('should return color2 when t=1', () => {
    expect(interpolateHexColor('#000000', '#ffffff', 1)).toBe('#ffffff');
  });

  it('should return a midpoint color when t=0.5', () => {
    const mid = interpolateHexColor('#000000', '#ffffff', 0.5);
    // Should be around #808080 (127 or 128 per channel)
    expect(mid).toMatch(/^#[78][0-9a-f][78][0-9a-f][78][0-9a-f]$/i);
  });
});

describe('faiColor', () => {
  it('should return blue-ish for FAI value 0', () => {
    const color = faiColor(0);
    expect(color).toBe('#3b82f6'); // blue start
  });

  it('should return red-ish for FAI value 2', () => {
    const color = faiColor(2);
    expect(color).toBe('#ef4444'); // red end
  });

  it('should clamp values above 2', () => {
    expect(faiColor(5)).toBe(faiColor(2));
  });

  it('should clamp values below 0', () => {
    expect(faiColor(-1)).toBe(faiColor(0));
  });
});

describe('TEST_STATUS_COLORS', () => {
  it('should define colors for all test statuses', () => {
    expect(TEST_STATUS_COLORS.passed).toBe('#2ecc71');
    expect(TEST_STATUS_COLORS.failed).toBe('#e74c3c');
    expect(TEST_STATUS_COLORS.skipped).toBe('#f1c40f');
    expect(TEST_STATUS_COLORS.error).toBe('#9b59b6');
  });
});
