import { useMemo } from 'react';
import chroma from 'chroma-js';
import type { ForecastResponse } from '../../api/types';

interface WindProfileChartProps {
  forecast?: ForecastResponse;
  className?: string;
}

interface HeightLayer {
  height: number;
  label: string;
  speed: number | null;
  direction: number | null;
}

const profileColor = chroma
  .scale(['#60a5fa', '#34d399', '#fbbf24', '#f87171'])
  .domain([0, 5, 10, 15])
  .mode('lab');

export default function WindProfileChart({ forecast, className }: WindProfileChartProps) {
  const layers = useMemo((): HeightLayer[] => {
    if (!forecast?.forecasts?.length) {
      return [
        { height: 120, label: '120m', speed: null, direction: null },
        { height: 80, label: '80m', speed: null, direction: null },
        { height: 10, label: '10m', speed: null, direction: null },
      ];
    }

    const current = forecast.forecasts[0];

    return [
      {
        height: 120,
        label: '120m',
        speed: current.wind_speed_120m ?? null,
        direction: current.wind_direction_120m ?? null,
      },
      {
        height: 80,
        label: '80m',
        speed: current.wind_speed_80m ?? null,
        direction: current.wind_direction_80m ?? null,
      },
      {
        height: 10,
        label: '10m',
        speed: current.wind_speed,
        direction: current.wind_direction,
      },
    ];
  }, [forecast]);

  const maxSpeed = Math.max(
    ...layers.map((l) => l.speed ?? 0),
    8, // minimum scale
  );

  // Calculate shear between layers
  const shearInfo = useMemo(() => {
    const validLayers = layers.filter((l) => l.speed !== null);
    if (validLayers.length < 2) return null;

    const top = validLayers[0];
    const bottom = validLayers[validLayers.length - 1];
    if (!top.speed || !bottom.speed || top.speed <= 0 || bottom.speed <= 0) return null;

    const alpha = Math.log(top.speed / bottom.speed) / Math.log(top.height / bottom.height);
    const assessment = alpha < 0.2 ? '低' : alpha < 0.35 ? '中' : '高';

    return { alpha: alpha.toFixed(2), assessment };
  }, [layers]);

  return (
    <div className={`card p-4 ${className || ''}`}>
      <h3 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-200">
        風速垂直剖面
      </h3>

      <div className="flex gap-4">
        {/* Profile visualization */}
        <div className="relative flex w-full flex-col gap-3">
          {layers.map((layer) => {
            const barWidth = layer.speed !== null ? (layer.speed / maxSpeed) * 100 : 0;
            const color = layer.speed !== null ? profileColor(Math.min(layer.speed, 15)).hex() : '#d1d5db';

            return (
              <div key={layer.height} className="flex items-center gap-3">
                {/* Height label */}
                <div className="w-10 text-right text-xs font-medium text-gray-500 dark:text-gray-400">
                  {layer.label}
                </div>

                {/* Bar */}
                <div className="relative flex-1">
                  <div className="h-7 w-full rounded bg-gray-100 dark:bg-gray-700">
                    <div
                      className="flex h-full items-center rounded transition-all duration-500"
                      style={{
                        width: `${Math.max(barWidth, 2)}%`,
                        backgroundColor: color,
                        opacity: 0.85,
                      }}
                    >
                      {layer.speed !== null && barWidth > 20 && (
                        <span className="ml-2 text-xs font-semibold text-white">
                          {layer.speed.toFixed(1)} m/s
                        </span>
                      )}
                    </div>
                  </div>
                  {/* Speed label outside bar when bar is too short */}
                  {layer.speed !== null && barWidth <= 20 && (
                    <span
                      className="absolute top-1/2 -translate-y-1/2 text-xs font-medium"
                      style={{ left: `${Math.max(barWidth, 2) + 2}%`, color }}
                    >
                      {layer.speed.toFixed(1)} m/s
                    </span>
                  )}
                  {layer.speed === null && (
                    <span className="absolute left-2 top-1/2 -translate-y-1/2 text-xs text-gray-400">
                      無資料
                    </span>
                  )}
                </div>

                {/* Direction arrow */}
                <div className="flex h-7 w-7 items-center justify-center">
                  {layer.direction !== null ? (
                    <svg viewBox="0 0 20 20" className="h-5 w-5">
                      <g transform={`rotate(${layer.direction}, 10, 10)`}>
                        <line x1="10" y1="10" x2="10" y2="3" stroke={color} strokeWidth="2" strokeLinecap="round" />
                        <polygon points="10,2 8,6 12,6" fill={color} />
                      </g>
                    </svg>
                  ) : (
                    <span className="text-xs text-gray-300">—</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Shear info */}
      {shearInfo && (
        <div className="mt-3 flex items-center gap-4 rounded-lg bg-gray-50 px-3 py-2 dark:bg-gray-700/50">
          <div className="text-xs">
            <span className="text-gray-500 dark:text-gray-400">風切變指數 </span>
            <span className="font-semibold text-gray-700 dark:text-gray-200">
              {shearInfo.alpha}
            </span>
          </div>
          <div className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
            shearInfo.assessment === '低'
              ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
              : shearInfo.assessment === '中'
                ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'
                : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
          }`}>
            {shearInfo.assessment}風切變
          </div>
        </div>
      )}

      {/* Scale */}
      <div className="mt-2 flex items-center justify-between text-[9px] text-gray-400">
        <span>0 m/s</span>
        <span>{Math.round(maxSpeed)} m/s</span>
      </div>
    </div>
  );
}
