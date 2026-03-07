import type { RiskLevel } from '../../api/types';
import { RISK_COLORS, RISK_LABELS } from '../../utils/colors';

const RISK_LEVELS: RiskLevel[] = ['green', 'yellow', 'red', 'black'];

export default function RiskLegend() {
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
