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

// ─── Gradient Color Scale (generic) ──────────────────────────
function gradientColor(
  value: number,
  min: number,
  max: number,
  stops: [number, string][],
): string {
  const clamped = Math.min(Math.max(value, min), max);
  if (clamped <= stops[0][0]) return stops[0][1];
  for (let i = 1; i < stops.length; i++) {
    if (clamped <= stops[i][0]) {
      const t = (clamped - stops[i - 1][0]) / (stops[i][0] - stops[i - 1][0]);
      return interpolateHexColor(stops[i - 1][1], stops[i][1], t);
    }
  }
  return stops[stops.length - 1][1];
}

// ─── Turbulence Color Scale (blue → yellow → red) ────────────
const TURBULENCE_STOPS: [number, string][] = [
  [0.1, '#3b82f6'],  // blue — 低湍流
  [0.25, '#22c55e'], // green — 適中
  [0.35, '#f59e0b'], // amber — 中等
  [0.50, '#ef4444'], // red — 高湍流
];

export function turbulenceColor(ti: number): string {
  return gradientColor(ti, 0.1, 0.5, TURBULENCE_STOPS);
}

// ─── Gust Factor Color Scale (green → orange → red) ─────────
const GUST_FACTOR_STOPS: [number, string][] = [
  [1.0, '#22c55e'],  // green — 低陣風
  [1.5, '#84cc16'],  // lime
  [2.0, '#f59e0b'],  // amber
  [2.5, '#f97316'],  // orange
  [3.0, '#ef4444'],  // red — 高陣風
];

export function gustFactorColor(gf: number): string {
  return gradientColor(gf, 1.0, 3.0, GUST_FACTOR_STOPS);
}

// ─── Shelter Index Color Scale (light → dark) ────────────────
const SHELTER_STOPS: [number, string][] = [
  [0.0, '#dbeafe'],  // blue-100 — 低遮蔽
  [0.3, '#60a5fa'],  // blue-400
  [0.6, '#2563eb'],  // blue-600
  [1.0, '#1e3a8a'],  // blue-900 — 高遮蔽
];

export function shelterColor(si: number): string {
  return gradientColor(si, 0.0, 1.0, SHELTER_STOPS);
}

// ─── Color Mode Metadata ─────────────────────────────────────
export type MapColorMode = 'risk' | 'turbulence' | 'gust_factor' | 'shelter' | 'wind_speed';

export const COLOR_MODE_LABELS: Record<MapColorMode, string> = {
  risk: '風險等級',
  turbulence: '湍流強度',
  gust_factor: '陣風因子',
  shelter: '遮蔽指數',
  wind_speed: '風速',
};

export const COLOR_MODE_LEGENDS: Record<MapColorMode, { label: string; color: string }[]> = {
  risk: [
    { label: '安全', color: RISK_COLORS.green },
    { label: '注意', color: RISK_COLORS.yellow },
    { label: '危險', color: RISK_COLORS.red },
    { label: '極度危險', color: RISK_COLORS.black },
  ],
  turbulence: [
    { label: '< 0.15 低', color: '#3b82f6' },
    { label: '0.25 適中', color: '#22c55e' },
    { label: '0.35 中等', color: '#f59e0b' },
    { label: '> 0.5 高', color: '#ef4444' },
  ],
  gust_factor: [
    { label: '< 1.5 低', color: '#22c55e' },
    { label: '2.0', color: '#f59e0b' },
    { label: '2.5', color: '#f97316' },
    { label: '> 3.0 高', color: '#ef4444' },
  ],
  shelter: [
    { label: '0 開闊', color: '#dbeafe' },
    { label: '0.3', color: '#60a5fa' },
    { label: '0.6', color: '#2563eb' },
    { label: '1.0 密集', color: '#1e3a8a' },
  ],
  wind_speed: [
    { label: '0 m/s', color: '#ffffb2' },
    { label: '6 m/s', color: '#fd8d3c' },
    { label: '9 m/s', color: '#f03b20' },
    { label: '15+ m/s', color: '#800026' },
  ],
};

// ─── Test Status Colors ────────────────────────────────────────
export const TEST_STATUS_COLORS = {
  passed: '#2ecc71',
  failed: '#e74c3c',
  skipped: '#f1c40f',
  error: '#9b59b6',
} as const;
