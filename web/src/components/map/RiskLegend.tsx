import type { RiskLevel } from '../../api/types';
import {
  RISK_COLORS,
  RISK_LABELS,
  COLOR_MODE_LABELS,
  COLOR_MODE_LEGENDS,
  COLOR_MODE_RANGES,
  gradientCSS,
} from '../../utils/colors';
import type { MapColorMode } from '../../utils/colors';

const RISK_LEVELS: RiskLevel[] = ['green', 'yellow', 'red', 'black'];

interface RiskLegendProps {
  colorMode?: MapColorMode;
}

export default function RiskLegend({ colorMode = 'risk' }: RiskLegendProps) {
  const title = COLOR_MODE_LABELS[colorMode];

  // Risk mode: categorical legend
  if (colorMode === 'risk') {
    return (
      <div className="rounded-md bg-white/95 p-3 shadow-md backdrop-blur dark:bg-gray-800/95">
        <h3 className="mb-2 text-xs font-semibold text-gray-600 dark:text-gray-300">
          風險等級
        </h3>
        <ul className="space-y-1">
          {RISK_LEVELS.map((level) => (
            <li key={level} className="flex items-center gap-2">
              <span
                className="inline-block h-3 w-5 rounded-sm"
                style={{ backgroundColor: RISK_COLORS[level] }}
                data-testid={`risk-color-${level}`}
              />
              <span className="text-xs text-gray-700 dark:text-gray-200">
                {RISK_LABELS[level].zh}
              </span>
              <span className="text-xs text-gray-400 dark:text-gray-500">
                {RISK_LABELS[level].en}
              </span>
            </li>
          ))}
        </ul>
      </div>
    );
  }

  // Continuous modes: gradient bar + discrete labels
  const range = COLOR_MODE_RANGES[colorMode];
  const legendItems = COLOR_MODE_LEGENDS[colorMode];

  return (
    <div className="rounded-md bg-white/95 p-3 shadow-md backdrop-blur dark:bg-gray-800/95">
      <h3 className="mb-2 text-xs font-semibold text-gray-600 dark:text-gray-300">
        {title}
      </h3>

      {/* Smooth gradient bar */}
      <div
        className="mb-2 h-3 w-full rounded-sm"
        style={{ background: gradientCSS(colorMode) }}
      />

      {/* Min/max labels under gradient */}
      <div className="mb-2 flex justify-between">
        <span className="text-[10px] text-gray-500 dark:text-gray-400">
          {range.min}{range.unit && ` ${range.unit}`}
        </span>
        <span className="text-[10px] text-gray-500 dark:text-gray-400">
          {range.max}{range.unit && ` ${range.unit}`}
        </span>
      </div>

      {/* Discrete reference labels */}
      <ul className="space-y-1">
        {legendItems.map((item) => (
          <li key={item.label} className="flex items-center gap-2">
            <span
              className="inline-block h-3 w-5 rounded-sm"
              style={{ backgroundColor: item.color }}
            />
            <span className="text-xs text-gray-700 dark:text-gray-200">
              {item.label}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
