import { useCallback, useMemo, useState } from "react";
import { Play, Pause } from "lucide-react";
import { useFlightStore } from "@/store/flight";

const HOURS_RANGE = 72;

function formatTime(date: Date): string {
  const month = date.getMonth() + 1;
  const day = date.getDate();
  const hours = date.getHours().toString().padStart(2, "0");
  return `${month}/${day} ${hours}:00`;
}

export function TimeSlider() {
  const { selectedTime, setTime } = useFlightStore();
  const [playing, setPlaying] = useState(false);

  const now = useMemo(() => new Date(), []);

  const hourOffset = useMemo(() => {
    return Math.round(
      (selectedTime.getTime() - now.getTime()) / (1000 * 60 * 60),
    );
  }, [selectedTime, now]);

  const handleSliderChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const offset = parseInt(e.target.value, 10);
      const newTime = new Date(now.getTime() + offset * 60 * 60 * 1000);
      setTime(newTime);
    },
    [now, setTime],
  );

  const handleNow = useCallback(() => {
    setTime(new Date());
  }, [setTime]);

  const togglePlay = useCallback(() => {
    setPlaying((p) => !p);
    // Auto-advance will be implemented with useEffect + setInterval
  }, []);

  return (
    <div className="absolute bottom-0 left-0 right-0 z-20 flex items-center gap-3 bg-gray-900/90 px-4 py-3 backdrop-blur-sm border-t border-gray-700/50">
      {/* 播放控制 */}
      <button
        onClick={togglePlay}
        className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-600 text-white hover:bg-blue-500 transition-colors"
      >
        {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
      </button>

      {/* 現在按鈕 */}
      <button
        onClick={handleNow}
        className="rounded-md bg-gray-700 px-3 py-1 text-xs text-white hover:bg-gray-600 transition-colors"
      >
        現在
      </button>

      {/* Slider */}
      <div className="flex-1 flex items-center gap-2">
        <span className="text-xs text-gray-400 w-16 text-right">
          {formatTime(
            new Date(now.getTime()),
          )}
        </span>
        <input
          type="range"
          min={0}
          max={HOURS_RANGE}
          value={Math.max(0, hourOffset)}
          onChange={handleSliderChange}
          className="flex-1 h-1.5 appearance-none bg-gray-700 rounded-full cursor-pointer
            [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-blue-500 [&::-webkit-slider-thumb]:cursor-grab"
        />
        <span className="text-xs text-gray-400 w-16">
          {formatTime(
            new Date(now.getTime() + HOURS_RANGE * 60 * 60 * 1000),
          )}
        </span>
      </div>

      {/* 當前時間顯示 */}
      <div className="rounded-md bg-gray-800 px-3 py-1 text-sm font-mono text-blue-400 border border-gray-600">
        {formatTime(selectedTime)}
      </div>
    </div>
  );
}
