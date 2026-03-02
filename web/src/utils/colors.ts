import type { RiskLevel } from '../api/types';

// ─── Risk Level Colors ─────────────────────────────────────────
export const RISK_COLORS: Record<RiskLevel, string> = {
  green: '#2ecc71',
  yellow: '#f1c40f',
  red: '#e74c3c',
  black: '#2c3e50',
};

export const RISK_LABELS: Record<RiskLevel, { zh: string; en: string }> = {
  green: { zh: '安全', en: 'Safe' },
  yellow: { zh: '注意', en: 'Caution' },
  red: { zh: '危險', en: 'Danger' },
  black: { zh: '極度危險', en: 'Extreme' },
};

export const RISK_LABELS_SHORT: Record<RiskLevel, string> = {
  green: 'Safe',
  yellow: 'Caution',
  red: 'Danger',
  black: 'Extreme',
};

// ─── Risk Level from Score ─────────────────────────────────────
export function riskLevelFromScore(score: number): RiskLevel {
  if (score < 25) return 'green';
  if (score < 50) return 'yellow';
  if (score < 75) return 'red';
  return 'black';
}

// ─── Risk Color from Score ─────────────────────────────────────
export function riskColorFromScore(score: number): string {
  return RISK_COLORS[riskLevelFromScore(score)];
}

// ─── Wind Speed Color (YlOrRd scale) ──────────────────────────
const WIND_SPEED_STOPS: [number, string][] = [
  [0, '#ffffb2'],
  [3, '#fecc5c'],
  [6, '#fd8d3c'],
  [9, '#f03b20'],
  [12, '#bd0026'],
  [15, '#800026'],
];

export function windSpeedColor(speed: number): string {
  if (speed <= WIND_SPEED_STOPS[0][0]) return WIND_SPEED_STOPS[0][1];

  for (let i = 1; i < WIND_SPEED_STOPS.length; i++) {
    const [prevSpeed, prevColor] = WIND_SPEED_STOPS[i - 1];
    const [currSpeed, currColor] = WIND_SPEED_STOPS[i];

    if (speed <= currSpeed) {
      const t = (speed - prevSpeed) / (currSpeed - prevSpeed);
      return interpolateHexColor(prevColor, currColor, t);
    }
  }

  return WIND_SPEED_STOPS[WIND_SPEED_STOPS.length - 1][1];
}

// ─── Hex Color Interpolation ───────────────────────────────────
function hexToRgb(hex: string): [number, number, number] {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  if (!result) return [0, 0, 0];
  return [
    parseInt(result[1], 16),
    parseInt(result[2], 16),
    parseInt(result[3], 16),
  ];
}

function rgbToHex(r: number, g: number, b: number): string {
  return (
    '#' +
    [r, g, b]
      .map((c) => {
        const hex = Math.round(c).toString(16);
        return hex.length === 1 ? '0' + hex : hex;
      })
      .join('')
  );
}

export function interpolateHexColor(
  color1: string,
  color2: string,
  t: number,
): string {
  const [r1, g1, b1] = hexToRgb(color1);
  const [r2, g2, b2] = hexToRgb(color2);
  return rgbToHex(
    r1 + (r2 - r1) * t,
    g1 + (g2 - g1) * t,
    b1 + (b2 - b1) * t,
  );
}

// ─── Corridor Colors ───────────────────────────────────────────
export const CORRIDOR_COLORS = {
  primary: '#3b82f6', // blue-500
  secondary: '#9ca3af', // gray-400
} as const;

// ─── FAI Color Scale ───────────────────────────────────────────
export function faiColor(value: number): string {
  // FAI typically 0-2+, map to blue-red scale
  const clamped = Math.min(Math.max(value, 0), 2);
  const t = clamped / 2;
  return interpolateHexColor('#3b82f6', '#ef4444', t);
}

// ─── Test Status Colors ────────────────────────────────────────
export const TEST_STATUS_COLORS = {
  passed: '#2ecc71',
  failed: '#e74c3c',
  skipped: '#f1c40f',
  error: '#9b59b6',
} as const;
