import { X, Wind, AlertTriangle, MapPin, Waves, Gauge, Shield } from 'lucide-react';
import type { GridCell } from '../../api/types';
import { RISK_COLORS, RISK_LABELS } from '../../utils/colors';
import { formatWindSpeed, formatCoords, formatRiskScore } from '../../utils/format';

interface GridPopupProps {
  cell: GridCell;
  onClose: () => void;
}

function tiLabel(ti: number): { text: string; color: string } {
  if (ti < 0.15) return { text: '極低', color: 'text-blue-600' };
  if (ti < 0.25) return { text: '低', color: 'text-green-600' };
  if (ti < 0.35) return { text: '中等', color: 'text-amber-600' };
  if (ti < 0.50) return { text: '高', color: 'text-red-500' };
  return { text: '極高', color: 'text-red-700' };
}

export default function GridPopup({ cell, onClose }: GridPopupProps) {
  const hasDerived = cell.turbulence != null || cell.gust_factor != null || cell.shelter_index != null;

  return (
    <div className="w-72 rounded-lg bg-white shadow-xl dark:bg-gray-800">
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

        {/* Derived data */}
        {hasDerived && (
          <div className="border-t border-gray-100 pt-2 dark:border-gray-700">
            {cell.turbulence != null && (
              <div className="flex items-center gap-2 py-0.5">
                <Waves size={12} className="shrink-0 text-gray-400" />
                <span className="text-xs text-gray-500 dark:text-gray-400">湍流</span>
                <span className={`ml-auto text-xs font-medium ${tiLabel(cell.turbulence).color}`}>
                  {cell.turbulence.toFixed(3)} ({tiLabel(cell.turbulence).text})
                </span>
              </div>
            )}
            {cell.gust_factor != null && (
              <div className="flex items-center gap-2 py-0.5">
                <Gauge size={12} className="shrink-0 text-gray-400" />
                <span className="text-xs text-gray-500 dark:text-gray-400">陣風因子</span>
                <span className="ml-auto text-xs font-medium text-gray-700 dark:text-gray-200">
                  ×{cell.gust_factor.toFixed(2)}
                  {cell.wind_speed > 0 && (
                    <span className="text-gray-400"> → {(cell.wind_speed * cell.gust_factor).toFixed(1)} m/s</span>
                  )}
                </span>
              </div>
            )}
            {cell.shelter_index != null && (
              <div className="flex items-center gap-2 py-0.5">
                <Shield size={12} className="shrink-0 text-gray-400" />
                <span className="text-xs text-gray-500 dark:text-gray-400">遮蔽指數</span>
                <span className="ml-auto text-xs font-medium text-gray-700 dark:text-gray-200">
                  {cell.shelter_index.toFixed(3)}
                </span>
              </div>
            )}
          </div>
        )}

        {cell.is_corridor && (
          <div className="mt-1 rounded bg-blue-50 px-2 py-1 text-xs text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
            此網格位於風廊範圍內
          </div>
        )}
      </div>
    </div>
  );
}
