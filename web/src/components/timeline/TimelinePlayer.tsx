import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Play, Pause, SkipForward, SkipBack, Clock } from 'lucide-react';
import chroma from 'chroma-js';
import clsx from 'clsx';

interface ForecastPoint {
  time: string;
  wind_speed: number;
  wind_direction: number;
  wind_gusts?: number | null;
  risk_level: string;
  wind_speed_80m?: number | null;
  wind_speed_120m?: number | null;
}

interface TimelinePlayerProps {
  forecasts: ForecastPoint[];
  currentIndex: number;
  onIndexChange: (index: number) => void;
  className?: string;
}

const SPEED_OPTIONS = [1, 2, 4];
const RISK_DOT_COLORS: Record<string, string> = {
  green: 'bg-green-400',
  yellow: 'bg-yellow-400',
  red: 'bg-red-500',
  black: 'bg-gray-800',
};

const speedColorScale = chroma
  .scale(['#60a5fa', '#34d399', '#fbbf24', '#f87171', '#991b1b'])
  .domain([0, 4, 8, 12, 18])
  .mode('lab');

export default function TimelinePlayer({
  forecasts,
  currentIndex,
  onIndexChange,
  className,
}: TimelinePlayerProps) {
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const intervalRef = useRef<number | null>(null);

  const stop = useCallback(() => {
    setPlaying(false);
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const play = useCallback(() => {
    if (forecasts.length === 0) return;
    setPlaying(true);
  }, [forecasts.length]);

  // Auto-advance
  useEffect(() => {
    if (!playing) {
      if (intervalRef.current) clearInterval(intervalRef.current);
      return;
    }

    intervalRef.current = window.setInterval(() => {
      onIndexChange(currentIndex + 1 >= forecasts.length ? 0 : currentIndex + 1);
    }, 1000 / speed);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [playing, speed, currentIndex, forecasts.length, onIndexChange]);

  // Pre-compute the mini sparkline bar chart
  const { maxSpeed, sparkBars } = useMemo(() => {
    const max = Math.max(...forecasts.map((f) => f.wind_speed), 1);
    const bars = forecasts.map((f, i) => ({
      height: (f.wind_speed / max) * 100,
      color: speedColorScale(Math.min(f.wind_speed, 18)).hex(),
      isHighRisk: f.risk_level === 'red' || f.risk_level === 'black',
      isCurrent: i === currentIndex,
    }));
    return { maxSpeed: max, sparkBars: bars };
  }, [forecasts, currentIndex]);

  if (forecasts.length === 0) return null;

  const current = forecasts[currentIndex] || forecasts[0];
  const currentTime = new Date(current.time);
  const formattedTime = currentTime.toLocaleString('zh-TW', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });

  // Detect day/night boundaries for timeline markers
  const dayNightMarkers = forecasts
    .map((f, i) => {
      const hour = new Date(f.time).getHours();
      if (hour === 6) return { index: i, type: 'sunrise' as const };
      if (hour === 18) return { index: i, type: 'sunset' as const };
      return null;
    })
    .filter((m): m is NonNullable<typeof m> => m !== null);

  return (
    <div
      className={clsx(
        'rounded-lg bg-white/95 px-3 py-2 shadow-lg backdrop-blur dark:bg-gray-800/95 md:px-4 md:py-3',
        className,
      )}
    >
      {/* Row 1: Controls + time + wind info */}
      <div className="flex items-center gap-2 md:gap-3">
        {/* Transport controls */}
        <div className="flex items-center gap-0.5 md:gap-1">
          <button
            onClick={() => onIndexChange(Math.max(0, currentIndex - 1))}
            className="rounded p-1 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
            title="上一小時"
          >
            <SkipBack size={14} />
          </button>
          <button
            onClick={() => (playing ? stop() : play())}
            className="rounded-full bg-blue-600 p-1.5 text-white hover:bg-blue-700"
            title={playing ? '暫停' : '播放'}
          >
            {playing ? <Pause size={14} /> : <Play size={14} />}
          </button>
          <button
            onClick={() => onIndexChange(Math.min(forecasts.length - 1, currentIndex + 1))}
            className="rounded p-1 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
            title="下一小時"
          >
            <SkipForward size={14} />
          </button>
        </div>

        {/* Current time display */}
        <div className="flex items-center gap-1 text-xs md:gap-1.5 md:text-sm">
          <Clock size={12} className="text-gray-400 md:hidden" />
          <Clock size={14} className="hidden text-gray-400 md:block" />
          <span className="font-mono font-medium text-gray-700 dark:text-gray-200">
            {formattedTime}
          </span>
        </div>

        {/* Wind info with color */}
        <div className="flex items-center gap-1.5 text-[11px] text-gray-500 dark:text-gray-400 md:gap-2 md:text-xs">
          <span
            className={clsx(
              'inline-block h-2 w-2 rounded-full md:h-2.5 md:w-2.5',
              RISK_DOT_COLORS[current.risk_level] || RISK_DOT_COLORS.green,
            )}
          />
          <span
            className="font-semibold"
            style={{ color: speedColorScale(Math.min(current.wind_speed, 18)).hex() }}
          >
            {current.wind_speed} m/s
          </span>
          {current.wind_gusts && (
            <span className="text-gray-400">
              (陣風 {current.wind_gusts} m/s)
            </span>
          )}
          <span className="hidden sm:inline">{current.wind_direction}°</span>
        </div>

        {/* Speed control */}
        <div className="ml-auto flex items-center gap-0.5 md:gap-1">
          {SPEED_OPTIONS.map((s) => (
            <button
              key={s}
              onClick={() => setSpeed(s)}
              className={clsx(
                'rounded px-1 py-0.5 text-[10px] font-medium md:px-1.5 md:text-xs',
                speed === s
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300',
              )}
            >
              {s}x
            </button>
          ))}
        </div>

        {/* Hour count */}
        <span className="text-[10px] text-gray-400 md:text-xs">
          {currentIndex + 1}/{forecasts.length}h
        </span>
      </div>

      {/* Row 2: Wind speed sparkline bar chart */}
      <div className="relative mt-2 flex h-6 items-end gap-px overflow-hidden rounded" role="presentation">
        {sparkBars.map((bar, i) => (
          <div
            key={i}
            className={clsx(
              'min-w-[1px] flex-1 cursor-pointer transition-opacity',
              bar.isCurrent ? 'opacity-100' : 'opacity-60 hover:opacity-90',
            )}
            style={{
              height: `${Math.max(bar.height, 4)}%`,
              backgroundColor: bar.color,
              borderTop: bar.isCurrent ? '2px solid white' : undefined,
            }}
            onClick={() => onIndexChange(i)}
            title={`${forecasts[i]?.wind_speed} m/s`}
          />
        ))}

        {/* Day/night markers */}
        {dayNightMarkers.map((m) => (
          <div
            key={`${m.type}-${m.index}`}
            className="pointer-events-none absolute bottom-0 top-0"
            style={{ left: `${(m.index / (forecasts.length - 1)) * 100}%` }}
          >
            <div
              className={clsx(
                'h-full w-px',
                m.type === 'sunrise' ? 'bg-amber-400/60' : 'bg-indigo-400/60',
              )}
            />
          </div>
        ))}
      </div>

      {/* Row 3: Timeline range labels */}
      <div className="mt-1 flex justify-between text-[9px] text-gray-400 md:text-[10px]">
        <span>
          {new Date(forecasts[0].time).toLocaleString('zh-TW', {
            month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false,
          })}
        </span>
        <span className="text-gray-300">
          最高 {Math.round(maxSpeed * 10) / 10} m/s
        </span>
        <span>
          {new Date(forecasts[forecasts.length - 1].time).toLocaleString('zh-TW', {
            month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false,
          })}
        </span>
      </div>
    </div>
  );
}
