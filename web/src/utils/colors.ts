import chroma from 'chroma-js';
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

// ─── Perceptual Color Scales (chroma.js Lab space) ─────────────
// These scales produce perceptually uniform gradients for scientific visualization

/** Wind speed: Viridis-inspired warm scale (light yellow → deep red) */
const windSpeedScale = chroma
  .scale(['#ffffb2', '#fecc5c', '#fd8d3c', '#f03b20', '#bd0026', '#800026'])
  .domain([0, 3, 6, 9, 12, 15])
  .mode('lab');

/** Turbulence intensity: blue → green → amber → red */
const turbulenceScale = chroma
  .scale(['#3b82f6', '#22c55e', '#f59e0b', '#ef4444'])
  .domain([0.1, 0.25, 0.35, 0.5])
  .mode('lab');

/** Gust factor: green → lime → amber → orange → red */
const gustFactorScale = chroma
  .scale(['#22c55e', '#84cc16', '#f59e0b', '#f97316', '#ef4444'])
  .domain([1.0, 1.5, 2.0, 2.5, 3.0])
  .mode('lab');

/** Shelter index: light blue → deep blue */
const shelterScale = chroma
  .scale(['#dbeafe', '#60a5fa', '#2563eb', '#1e3a8a'])
  .domain([0.0, 0.3, 0.6, 1.0])
  .mode('lab');

/** FAI: blue → red */
const faiScale = chroma
  .scale(['#3b82f6', '#ef4444'])
  .domain([0, 2])
  .mode('lab');

// ─── Accessibility: Color-blind friendly scales ────────────────

/** Viridis scale for wind speed (color-blind safe) */
const windSpeedViridis = chroma
  .scale(['#440154', '#482777', '#3e4989', '#31688e', '#26828e', '#1f9e89', '#35b779', '#6ece58', '#b5de2b', '#fde725'])
  .domain([0, 15])
  .mode('lab');

/** Cividis scale (color-blind optimized, blue-yellow) */
const windSpeedCividis = chroma
  .scale(['#00204d', '#414d6b', '#7b7b78', '#bcaf6f', '#ffea46'])
  .domain([0, 15])
  .mode('lab');

export type AccessibilityMode = 'default' | 'viridis' | 'cividis';

let currentAccessibilityMode: AccessibilityMode = 'default';

export function setAccessibilityMode(mode: AccessibilityMode): void {
  currentAccessibilityMode = mode;
}

export function getAccessibilityMode(): AccessibilityMode {
  return currentAccessibilityMode;
}

// ─── Wind Speed Color ──────────────────────────────────────────
const WIND_SPEED_STOPS: [number, string][] = [
  [0, '#ffffb2'],
  [3, '#fecc5c'],
  [6, '#fd8d3c'],
  [9, '#f03b20'],
  [12, '#bd0026'],
  [15, '#800026'],
];

export function windSpeedColor(speed: number): string {
  // Use accessibility mode scales when active
  if (currentAccessibilityMode === 'viridis') {
    const clamped = Math.min(Math.max(speed, 0), 15);
    return windSpeedViridis(clamped).hex();
  }
  if (currentAccessibilityMode === 'cividis') {
    const clamped = Math.min(Math.max(speed, 0), 15);
    return windSpeedCividis(clamped).hex();
  }

  // Default: use exact stop colors for backward compatibility
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

/**
 * Get wind speed color using chroma.js Lab-space interpolation.
 * Produces smoother, more perceptually uniform gradients.
 */
export function windSpeedColorLab(speed: number): string {
  const clamped = Math.min(Math.max(speed, 0), 15);
  return windSpeedScale(clamped).hex();
}

// ─── Hex Color Interpolation (legacy) ─────────────────────────
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

/**
 * Interpolate between two colors in Lab space for perceptual uniformity.
 */
export function interpolateColorLab(
  color1: string,
  color2: string,
  t: number,
): string {
  return chroma.mix(color1, color2, t, 'lab').hex();
}

// ─── Corridor Colors ───────────────────────────────────────────
export const CORRIDOR_COLORS = {
  primary: '#3b82f6', // blue-500
  secondary: '#9ca3af', // gray-400
} as const;

// ─── FAI Color Scale ───────────────────────────────────────────
export function faiColor(value: number): string {
  // Maintain exact backward compatibility at boundaries
  const clamped = Math.min(Math.max(value, 0), 2);
  if (clamped === 0) return '#3b82f6';
  if (clamped === 2) return '#ef4444';
  return faiScale(clamped).hex();
}

// ─── Turbulence Color Scale ────────────────────────────────────
export function turbulenceColor(ti: number): string {
  const clamped = Math.min(Math.max(ti, 0.1), 0.5);
  return turbulenceScale(clamped).hex();
}

// ─── Gust Factor Color Scale ───────────────────────────────────
export function gustFactorColor(gf: number): string {
  const clamped = Math.min(Math.max(gf, 1.0), 3.0);
  return gustFactorScale(clamped).hex();
}

// ─── Shelter Index Color Scale ─────────────────────────────────
export function shelterColor(si: number): string {
  const clamped = Math.min(Math.max(si, 0.0), 1.0);
  return shelterScale(clamped).hex();
}

// ─── Continuous Gradient Bar (for legends) ─────────────────────

/**
 * Generate an array of color stops for CSS gradient rendering.
 * Used to create smooth gradient legends instead of discrete color blocks.
 */
export function generateGradientStops(
  mode: MapColorMode,
  steps = 20,
): { color: string; position: number }[] {
  const stops: { color: string; position: number }[] = [];

  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    let color: string;

    switch (mode) {
      case 'wind_speed':
        color = windSpeedScale(t * 15).hex();
        break;
      case 'turbulence':
        color = turbulenceScale(0.1 + t * 0.4).hex();
        break;
      case 'gust_factor':
        color = gustFactorScale(1.0 + t * 2.0).hex();
        break;
      case 'shelter':
        color = shelterScale(t).hex();
        break;
      case 'risk':
      default: {
        const riskScale = chroma
          .scale([RISK_COLORS.green, RISK_COLORS.yellow, RISK_COLORS.red, RISK_COLORS.black])
          .mode('lab');
        color = riskScale(t).hex();
        break;
      }
    }

    stops.push({ color, position: t * 100 });
  }

  return stops;
}

/**
 * Generate a CSS linear-gradient string for use in legend bars.
 */
export function gradientCSS(mode: MapColorMode, direction = 'to right'): string {
  const stops = generateGradientStops(mode, 10);
  const colorStops = stops.map((s) => `${s.color} ${s.position}%`).join(', ');
  return `linear-gradient(${direction}, ${colorStops})`;
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

// ─── Value Range Metadata (for contour generation) ─────────────
export const COLOR_MODE_RANGES: Record<MapColorMode, { min: number; max: number; unit: string }> = {
  risk: { min: 0, max: 100, unit: '' },
  turbulence: { min: 0.1, max: 0.5, unit: '' },
  gust_factor: { min: 1.0, max: 3.0, unit: '' },
  shelter: { min: 0, max: 1, unit: '' },
  wind_speed: { min: 0, max: 15, unit: 'm/s' },
};

/**
 * Get the color for any value in any color mode using Lab-space interpolation.
 */
export function colorForValue(mode: MapColorMode, value: number): string {
  switch (mode) {
    case 'wind_speed':
      return windSpeedColorLab(value);
    case 'turbulence':
      return turbulenceColor(value);
    case 'gust_factor':
      return gustFactorColor(value);
    case 'shelter':
      return shelterColor(value);
    case 'risk':
    default:
      return riskColorFromScore(value);
  }
}

// ─── Test Status Colors ────────────────────────────────────────
export const TEST_STATUS_COLORS = {
  passed: '#2ecc71',
  failed: '#e74c3c',
  skipped: '#f1c40f',
  error: '#9b59b6',
} as const;
