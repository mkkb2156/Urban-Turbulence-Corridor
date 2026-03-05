import { useState, useEffect, useRef, useCallback } from 'react';
import { Play, Pause, SkipForward, SkipBack, Clock } from 'lucide-react';
import clsx from 'clsx';

interface ForecastPoint {
  time: string;
  wind_speed: number;
  wind_direction: number;
  wind_gusts: number;
  risk_level: string;
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

  // Find key moments (risk >= red)
  const keyMoments = forecasts
    .map((f, i) => ({ index: i, risk: f.risk_level }))
    .filter((m) => m.risk === 'red' || m.risk === 'black');

  return (
    <div
      className={clsx(
        'flex items-center gap-3 rounded-lg bg-white px-4 py-3 shadow-lg dark:bg-gray-800',
        className,
      )}
    >
      {/* Transport controls */}
      <div className="flex items-center gap-1">
        <button
          onClick={() => onIndexChange(Math.max(0, currentIndex - 1))}
          className="rounded p-1 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
          title="Previous hour"
        >
          <SkipBack size={16} />
        </button>
        <button
          onClick={() => (playing ? stop() : play())}
          className="rounded-full bg-blue-600 p-1.5 text-white hover:bg-blue-700"
          title={playing ? 'Pause' : 'Play'}
        >
          {playing ? <Pause size={16} /> : <Play size={16} />}
        </button>
        <button
          onClick={() => onIndexChange(Math.min(forecasts.length - 1, currentIndex + 1))}
          className="rounded p-1 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
          title="Next hour"
        >
          <SkipForward size={16} />
        </button>
      </div>

      {/* Current time display */}
      <div className="flex items-center gap-1.5 text-sm">
        <Clock size={14} className="text-gray-400" />
        <span className="font-mono font-medium text-gray-700 dark:text-gray-200">
          {formattedTime}
        </span>
      </div>

      {/* Wind info */}
      <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
        <span
          className={clsx(
            'inline-block h-2.5 w-2.5 rounded-full',
            RISK_DOT_COLORS[current.risk_level] || RISK_DOT_COLORS.green,
          )}
        />
        <span>{current.wind_speed} m/s</span>
        <span>{current.wind_direction}°</span>
      </div>

      {/* Timeline slider */}
      <div className="relative flex-1">
        <input
          type="range"
          min={0}
          max={forecasts.length - 1}
          value={currentIndex}
          onChange={(e) => onIndexChange(Number(e.target.value))}
          className="h-2 w-full cursor-pointer appearance-none rounded-lg bg-gray-200 accent-blue-600 dark:bg-gray-600"
        />
        {/* Key moment markers */}
        <div className="absolute left-0 right-0 top-0 h-2 pointer-events-none">
          {keyMoments.map((m) => (
            <div
              key={m.index}
              className="absolute top-0 h-2 w-1 rounded-full bg-red-500"
              style={{ left: `${(m.index / (forecasts.length - 1)) * 100}%` }}
            />
          ))}
        </div>
      </div>

      {/* Speed control */}
      <div className="flex items-center gap-1">
        {SPEED_OPTIONS.map((s) => (
          <button
            key={s}
            onClick={() => setSpeed(s)}
            className={clsx(
              'rounded px-1.5 py-0.5 text-xs font-medium',
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
      <span className="text-xs text-gray-400">
        {currentIndex + 1}/{forecasts.length}h
      </span>
    </div>
  );
}
