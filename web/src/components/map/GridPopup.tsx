import { X, Wind, AlertTriangle, MapPin } from 'lucide-react';
import type { GridCell } from '../../api/types';
import { RISK_COLORS, RISK_LABELS } from '../../utils/colors';
import { formatWindSpeed, formatCoords, formatRiskScore } from '../../utils/format';

interface GridPopupProps {
  cell: GridCell;
  onClose: () => void;
}

export default function GridPopup({ cell, onClose }: GridPopupProps) {
  return (
    <div className="w-64 rounded-lg bg-white shadow-xl dark:bg-gray-800">
      {/* Header */}
      <div
        className="flex items-center justify-between rounded-t-lg px-3 py-2"
        style={{ backgroundColor: RISK_COLORS[cell.risk_level] + '20' }}
      >
        <div className="flex items-center gap-2">
          <span
            className="inline-block h-3 w-3 rounded-full"
            style={{ backgroundColor: RISK_COLORS[cell.risk_level] }}
          />
          <span className="text-sm font-semibold text-gray-800 dark:text-gray-100">
            {RISK_LABELS[cell.risk_level].zh} / {RISK_LABELS[cell.risk_level].en}
          </span>
        </div>
        <button
          onClick={onClose}
          className="rounded p-0.5 text-gray-500 hover:bg-gray-200 dark:text-gray-400 dark:hover:bg-gray-600"
          aria-label="關閉彈窗"
        >
          <X size={14} />
        </button>
      </div>

      {/* Body */}
      <div className="space-y-2.5 px-3 py-3">
        <div className="flex items-start gap-2">
          <MapPin size={14} className="mt-0.5 shrink-0 text-gray-400" />
          <div>
            <div className="text-xs text-gray-500 dark:text-gray-400">網格 ID</div>
            <div className="text-sm font-mono text-gray-800 dark:text-gray-100">
              {cell.grid_id}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">
              {formatCoords(cell.lon, cell.lat)}
            </div>
          </div>
        </div>

        <div className="flex items-start gap-2">
          <Wind size={14} className="mt-0.5 shrink-0 text-gray-400" />
          <div>
            <div className="text-xs text-gray-500 dark:text-gray-400">風場</div>
            <div className="text-sm text-gray-800 dark:text-gray-100">
              {formatWindSpeed(cell.wind_speed)} 來自 {cell.wind_direction}
            </div>
          </div>
        </div>

        <div className="flex items-start gap-2">
          <AlertTriangle size={14} className="mt-0.5 shrink-0 text-gray-400" />
          <div>
            <div className="text-xs text-gray-500 dark:text-gray-400">風險分數</div>
            <div className="text-sm text-gray-800 dark:text-gray-100">
              {formatRiskScore(cell.risk_score)}
            </div>
          </div>
        </div>

        {cell.is_corridor && (
          <div className="mt-1 rounded bg-blue-50 px-2 py-1 text-xs text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
            此網格位於風廊範圍內
          </div>
        )}
      </div>
    </div>
  );
}
