import { useMemo } from 'react';
import { Wind, Navigation, AlertTriangle, Gauge } from 'lucide-react';
import chroma from 'chroma-js';
import type { ForecastResponse } from '../../api/types';

interface WeatherCardProps {
  forecast?: ForecastResponse;
  isLoading?: boolean;
}

const speedColor = chroma
  .scale(['#60a5fa', '#34d399', '#fbbf24', '#f87171', '#991b1b'])
  .domain([0, 4, 8, 12, 18])
  .mode('lab');

const RISK_CONFIG: Record<string, { bg: string; text: string; label: string }> = {
  green: { bg: 'bg-emerald-500/10', text: 'text-emerald-600 dark:text-emerald-400', label: '安全' },
  yellow: { bg: 'bg-amber-500/10', text: 'text-amber-600 dark:text-amber-400', label: '注意' },
  red: { bg: 'bg-red-500/10', text: 'text-red-600 dark:text-red-400', label: '危險' },
  black: { bg: 'bg-gray-800/10', text: 'text-gray-800 dark:text-gray-200', label: '極度危險' },
};

function WindCompass({ direction, speed }: { direction: number; speed: number }) {
  const color = speedColor(Math.min(speed, 18)).hex();
  return (
    <div className="relative flex h-20 w-20 items-center justify-center">
      {/* Compass ring */}
      <svg viewBox="0 0 100 100" className="absolute inset-0 h-full w-full">
        <circle cx="50" cy="50" r="44" fill="none" stroke="currentColor" strokeWidth="1"
          className="text-gray-200 dark:text-gray-600" />
        {/* Cardinal markers */}
        {['N', 'E', 'S', 'W'].map((label, i) => {
          const angle = i * 90;
          const rad = (angle - 90) * Math.PI / 180;
          const x = 50 + 38 * Math.cos(rad);
          const y = 50 + 38 * Math.sin(rad);
          return (
            <text key={label} x={x} y={y} textAnchor="middle" dominantBaseline="central"
              className="fill-gray-400 dark:fill-gray-500" fontSize="8" fontWeight="bold"
            >
              {label}
            </text>
          );
        })}
        {/* Wind direction arrow */}
        <g transform={`rotate(${direction}, 50, 50)`}>
          <line x1="50" y1="50" x2="50" y2="18" stroke={color} strokeWidth="2.5" strokeLinecap="round" />
          <polygon points="50,14 46,22 54,22" fill={color} />
        </g>
        {/* Center dot */}
        <circle cx="50" cy="50" r="3" fill={color} />
      </svg>
    </div>
  );
}

export default function WeatherCard({ forecast, isLoading }: WeatherCardProps) {
  const { current, next6h, gustWarning } = useMemo(() => {
    if (!forecast?.forecasts?.length) {
      return { current: null, next6h: [], gustWarning: false };
    }

    const now = forecast.forecasts[0];
    const next = forecast.forecasts.slice(0, 6);
    const maxGusts = Math.max(...next.map((f) => f.wind_gusts ?? 0));

    return {
      current: now,
      next6h: next,
      gustWarning: maxGusts > 10,
    };
  }, [forecast]);

  if (isLoading) {
    return (
      <div className="card animate-pulse p-5">
        <div className="h-6 w-32 rounded bg-gray-200 dark:bg-gray-700" />
        <div className="mt-4 h-20 w-full rounded bg-gray-200 dark:bg-gray-700" />
      </div>
    );
  }

  if (!current) return null;

  const riskConfig = RISK_CONFIG[current.risk_level] || RISK_CONFIG.green;
  const currentColor = speedColor(Math.min(current.wind_speed, 18)).hex();

  return (
    <div className="card overflow-hidden p-0">
      {/* Header with gradient */}
      <div
        className="px-5 pb-4 pt-5"
        style={{
          background: `linear-gradient(135deg, ${chroma(currentColor).alpha(0.12).css()}, transparent)`,
        }}
      >
        <div className="flex items-start justify-between">
          {/* Left: Wind speed + status */}
          <div>
            <div className="flex items-baseline gap-2">
              <span
                className="text-4xl font-bold tracking-tight"
                style={{ color: currentColor }}
              >
                {current.wind_speed}
              </span>
              <span className="text-lg text-gray-400">m/s</span>
            </div>

            <div className={`mt-1 inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${riskConfig.bg} ${riskConfig.text}`}>
              <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: currentColor }} />
              {riskConfig.label}
            </div>

            {current.wind_gusts && (
              <div className="mt-2 flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                <Gauge size={12} />
                <span>陣風 {current.wind_gusts} m/s</span>
              </div>
            )}
          </div>

          {/* Right: Wind compass */}
          <WindCompass direction={current.wind_direction} speed={current.wind_speed} />
        </div>

        {/* Gust warning */}
        {gustWarning && (
          <div className="mt-3 flex items-center gap-2 rounded-lg bg-amber-50 px-3 py-2 dark:bg-amber-900/20">
            <AlertTriangle size={14} className="shrink-0 text-amber-500" />
            <span className="text-xs text-amber-700 dark:text-amber-300">
              未來 6 小時預測有強陣風
            </span>
          </div>
        )}
      </div>

      {/* 6-hour forecast strip */}
      <div className="border-t border-gray-100 px-5 py-3 dark:border-gray-700">
        <div className="mb-2 flex items-center gap-1 text-[10px] font-medium uppercase tracking-wider text-gray-400">
          <Wind size={10} />
          <span>未來 6 小時</span>
        </div>
        <div className="flex items-end justify-between gap-1">
          {next6h.map((point, i) => {
            const barColor = speedColor(Math.min(point.wind_speed, 18)).hex();
            const maxSpeed = Math.max(...next6h.map((p) => p.wind_speed), 1);
            const barHeight = Math.max((point.wind_speed / maxSpeed) * 32, 4);
            const hour = new Date(point.time).getHours();

            return (
              <div key={i} className="flex flex-1 flex-col items-center gap-1">
                <span className="text-[10px] font-medium" style={{ color: barColor }}>
                  {point.wind_speed}
                </span>
                <div
                  className="w-full rounded-sm"
                  style={{
                    height: barHeight,
                    backgroundColor: barColor,
                    opacity: 0.7,
                  }}
                />
                <span className="text-[9px] text-gray-400">
                  {hour}:00
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Source badge */}
      <div className="border-t border-gray-100 px-5 py-2 dark:border-gray-700">
        <div className="flex items-center justify-between text-[10px] text-gray-400">
          <span className="flex items-center gap-1">
            <Navigation size={8} />
            {forecast?.source === 'open-meteo' ? 'Open-Meteo' : '模擬資料'}
          </span>
          <span>
            {forecast?.generated_at
              ? new Date(forecast.generated_at).toLocaleString('zh-TW', {
                  hour: '2-digit', minute: '2-digit', hour12: false,
                })
              : ''}
          </span>
        </div>
      </div>
    </div>
  );
}
