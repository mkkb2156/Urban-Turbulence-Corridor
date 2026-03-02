// ─── Number Formatting ─────────────────────────────────────────

/**
 * Format a number to a fixed number of decimal places.
 */
export function toFixed(value: number, decimals = 2): string {
  return value.toFixed(decimals);
}

/**
 * Format wind speed with unit (m/s).
 */
export function formatWindSpeed(speed: number): string {
  return `${toFixed(speed, 1)} m/s`;
}

/**
 * Format risk score as percentage (0-100).
 */
export function formatRiskScore(score: number): string {
  return `${Math.round(score)}%`;
}

/**
 * Format a percentage value with a % symbol.
 */
export function formatPercentage(value: number, decimals = 1): string {
  return `${toFixed(value, decimals)}%`;
}

// ─── Coordinate Formatting ─────────────────────────────────────

/**
 * Format longitude value (e.g., 121.5500 E).
 */
export function formatLon(lon: number): string {
  const dir = lon >= 0 ? 'E' : 'W';
  return `${toFixed(Math.abs(lon), 4)}\u00B0 ${dir}`;
}

/**
 * Format latitude value (e.g., 25.0300 N).
 */
export function formatLat(lat: number): string {
  const dir = lat >= 0 ? 'N' : 'S';
  return `${toFixed(Math.abs(lat), 4)}\u00B0 ${dir}`;
}

/**
 * Format lon/lat pair as a readable string.
 */
export function formatCoords(lon: number, lat: number): string {
  return `${formatLat(lat)}, ${formatLon(lon)}`;
}

/**
 * Format height with unit (m AGL).
 */
export function formatHeight(height: number): string {
  return `${height}m AGL`;
}

// ─── Date/Time Formatting ──────────────────────────────────────

/**
 * Format an ISO date string to a localized date-time string.
 */
export function formatDateTime(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleString('zh-TW', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
}

/**
 * Format a duration in milliseconds to a human-readable string.
 */
export function formatDuration(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  if (ms < 60000) return `${toFixed(ms / 1000, 1)}s`;
  const minutes = Math.floor(ms / 60000);
  const seconds = Math.round((ms % 60000) / 1000);
  return `${minutes}m ${seconds}s`;
}

/**
 * Format a relative time (e.g., "3 minutes ago").
 */
export function formatRelativeTime(isoString: string): string {
  const now = Date.now();
  const then = new Date(isoString).getTime();
  const diffMs = now - then;

  if (diffMs < 60000) return 'just now';
  if (diffMs < 3600000) {
    const mins = Math.floor(diffMs / 60000);
    return `${mins} minute${mins > 1 ? 's' : ''} ago`;
  }
  if (diffMs < 86400000) {
    const hours = Math.floor(diffMs / 3600000);
    return `${hours} hour${hours > 1 ? 's' : ''} ago`;
  }
  const days = Math.floor(diffMs / 86400000);
  return `${days} day${days > 1 ? 's' : ''} ago`;
}

// ─── Number Abbreviation ───────────────────────────────────────

/**
 * Abbreviate large numbers (e.g., 1200 -> "1.2K").
 */
export function abbreviateNumber(value: number): string {
  if (value < 1000) return String(value);
  if (value < 1_000_000) return `${toFixed(value / 1000, 1)}K`;
  return `${toFixed(value / 1_000_000, 1)}M`;
}
