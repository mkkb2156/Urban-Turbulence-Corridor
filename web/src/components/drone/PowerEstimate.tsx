import { Zap, Clock, Navigation, AlertTriangle } from 'lucide-react';
import clsx from 'clsx';
import type { DronePowerResponse } from '../../api/types';

interface PowerEstimateProps {
  data: DronePowerResponse;
}

export default function PowerEstimate({ data }: PowerEstimateProps) {
  const batteryUsedPct = data.battery_impact_pct;
  const isHighImpact = batteryUsedPct > 20;
  const isCritical = batteryUsedPct > 40;

  return (
    <div className="card space-y-3">
      <div className="flex items-center gap-2">
        <Zap size={16} className="text-yellow-500" />
        <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-200">
          電池影響估算
        </h4>
        <span className="text-xs text-gray-400">{data.drone_name}</span>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
        <div>
          <p className="text-xs text-gray-500 dark:text-gray-400">懸停功率</p>
          <p className="font-medium text-gray-800 dark:text-gray-100">
            {data.hover_power_w} W
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 dark:text-gray-400">飛行功率</p>
          <p className="font-medium text-gray-800 dark:text-gray-100">
            {data.forward_power_w} W
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            <Clock size={10} className="mr-1 inline" />
            預估續航
          </p>
          <p className="font-medium text-gray-800 dark:text-gray-100">
            {data.endurance_min} 分鐘
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            <Navigation size={10} className="mr-1 inline" />
            預估航程
          </p>
          <p className="font-medium text-gray-800 dark:text-gray-100">
            {data.range_km} km
          </p>
        </div>
      </div>

      {/* 電池影響條 */}
      <div>
        <div className="mb-1 flex items-center justify-between text-xs">
          <span className="text-gray-500 dark:text-gray-400">
            風對電池影響
          </span>
          <span
            className={clsx(
              'font-medium',
              isCritical ? 'text-red-600' : isHighImpact ? 'text-yellow-600' : 'text-green-600',
            )}
          >
            {batteryUsedPct > 0 ? '-' : ''}{Math.abs(batteryUsedPct).toFixed(1)}%
          </span>
        </div>
        <div className="h-2 w-full rounded-full bg-gray-200 dark:bg-gray-700">
          <div
            className={clsx(
              'h-2 rounded-full transition-all',
              isCritical ? 'bg-red-500' : isHighImpact ? 'bg-yellow-500' : 'bg-green-500',
            )}
            style={{ width: `${Math.min(100, Math.abs(batteryUsedPct))}%` }}
          />
        </div>
      </div>

      {/* 風場分量 */}
      <div className="flex gap-4 text-xs text-gray-500 dark:text-gray-400">
        <span>
          逆風: <span className="font-medium text-gray-700 dark:text-gray-300">{data.headwind_ms} m/s</span>
        </span>
        <span>
          側風: <span className="font-medium text-gray-700 dark:text-gray-300">{data.crosswind_ms} m/s</span>
        </span>
        <span>
          地速: <span className="font-medium text-gray-700 dark:text-gray-300">{data.groundspeed_ms} m/s</span>
        </span>
      </div>

      {isCritical && (
        <div className="flex items-center gap-2 rounded-md bg-red-50 px-3 py-2 text-xs text-red-700 dark:bg-red-900/20 dark:text-red-300">
          <AlertTriangle size={14} />
          風速對續航影響超過 40%，建議降低飛行速度或等待風速下降
        </div>
      )}
    </div>
  );
}
