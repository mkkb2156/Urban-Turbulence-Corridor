import { useState } from 'react';
import { Wind, ArrowRight, RefreshCw, Compass } from 'lucide-react';
import clsx from 'clsx';
import { useCorridors, useCorridorCompute, useGridCells } from '../api/hooks';
import type { HeightOption, MapLayers, Corridor } from '../api/types';
import { DEFAULT_MAP_LAYERS } from '../api/types';
import { RISK_COLORS, RISK_LABELS, CORRIDOR_COLORS } from '../utils/colors';
import { formatWindSpeed } from '../utils/format';
import WindMap from '../components/map/WindMap';

const WIND_DIRECTIONS = [
  { label: 'NE', deg: 45, description: '東北季風（10-4月）' },
  { label: 'SW', deg: 225, description: '西南季風（6-9月）' },
  { label: 'N', deg: 0, description: '北風' },
  { label: 'E', deg: 90, description: '東風' },
  { label: 'S', deg: 180, description: '南風' },
  { label: 'W', deg: 270, description: '西風' },
] as const;

export default function CorridorPage() {
  const [height, setHeight] = useState<HeightOption>(50);
  const [layers, setLayers] = useState<MapLayers>({
    ...DEFAULT_MAP_LAYERS,
    corridors: true,
  });
  const [selectedCorridor, setSelectedCorridor] = useState<Corridor | null>(null);
  const [selectedDirection, setSelectedDirection] = useState<number | null>(null);

  const { data: corridors, isLoading: corridorsLoading } = useCorridors();
  const { data: gridCells, isLoading: gridsLoading } = useGridCells(height);
  const corridorCompute = useCorridorCompute();

  // 使用計算結果（如有）或 DB 資料
  const displayCorridors = corridorCompute.data ?? corridors;
  const isLoading = corridorsLoading || corridorCompute.isPending;

  const handleDirectionClick = (deg: number) => {
    if (selectedDirection === deg) {
      // 取消選擇 → 顯示 DB 原始風廊
      setSelectedDirection(null);
      corridorCompute.reset();
      return;
    }
    setSelectedDirection(deg);
    setSelectedCorridor(null);
    corridorCompute.mutate({
      city: 'taipei',
      wind_direction: deg,
      n_corridors: 5,
    });
  };

  const handleMultiDirection = () => {
    setSelectedDirection(null);
    setSelectedCorridor(null);
    corridorCompute.mutate({
      city: 'taipei',
      wind_direction: 45,
      n_corridors: 5,
      multi_direction: true,
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">
          風廊
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          已識別的城市風廊及其特性 — 支援多風向即時計算
        </p>
      </div>

      {/* 風向選擇器 */}
      <div className="card">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-600 dark:text-gray-300">
            <Compass size={16} />
            風向篩選
          </h3>
          <button
            onClick={handleMultiDirection}
            disabled={corridorCompute.isPending}
            className="flex items-center gap-1 rounded-md bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-700 transition-colors hover:bg-blue-100 disabled:opacity-50 dark:bg-blue-900/30 dark:text-blue-300 dark:hover:bg-blue-900/50"
          >
            <RefreshCw size={12} className={corridorCompute.isPending ? 'animate-spin' : ''} />
            多方向分析
          </button>
        </div>
        <div className="flex flex-wrap gap-2">
          {WIND_DIRECTIONS.map((dir) => (
            <button
              key={dir.label}
              onClick={() => handleDirectionClick(dir.deg)}
              disabled={corridorCompute.isPending}
              className={clsx(
                'rounded-lg px-3 py-1.5 text-xs font-medium transition-all',
                selectedDirection === dir.deg
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600',
                corridorCompute.isPending && 'opacity-50',
              )}
              title={dir.description}
            >
              {dir.label} ({dir.deg}°)
            </button>
          ))}
        </div>
        {corridorCompute.isError && (
          <p className="mt-2 text-xs text-red-500">
            計算失敗: {corridorCompute.error?.message ?? '未知錯誤'}
          </p>
        )}
        {corridorCompute.data && (
          <p className="mt-2 text-xs text-green-600 dark:text-green-400">
            即時計算完成: {corridorCompute.data.length} 條風廊
          </p>
        )}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Corridor list */}
        <div className="space-y-3 lg:col-span-1">
          <h3 className="text-sm font-semibold text-gray-600 dark:text-gray-300">
            {corridorCompute.data ? '計算結果' : '已偵測風廊'}
          </h3>

          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="card animate-pulse">
                  <div className="h-4 w-32 rounded bg-gray-200 dark:bg-gray-700" />
                  <div className="mt-2 h-3 w-24 rounded bg-gray-200 dark:bg-gray-700" />
                </div>
              ))}
            </div>
          ) : displayCorridors && displayCorridors.length > 0 ? (
            <ul className="space-y-2">
              {displayCorridors.map((corridor) => (
                <li key={corridor.corridor_id}>
                  <button
                    onClick={() => setSelectedCorridor(corridor)}
                    className={clsx(
                      'card w-full text-left transition-shadow hover:shadow-md',
                      selectedCorridor?.corridor_id === corridor.corridor_id &&
                        'ring-2 ring-blue-500',
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <div
                        className="h-3 w-3 rounded-full"
                        style={{
                          backgroundColor:
                            corridor.type === 'primary'
                              ? CORRIDOR_COLORS.primary
                              : CORRIDOR_COLORS.secondary,
                        }}
                      />
                      <span className="text-sm font-medium text-gray-800 dark:text-gray-100">
                        {corridor.name}
                      </span>
                      <span
                        className={clsx(
                          'ml-auto rounded px-1.5 py-0.5 text-xs',
                          corridor.type === 'primary'
                            ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300'
                            : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400',
                        )}
                      >
                        {corridor.type}
                      </span>
                    </div>
                    <div className="mt-2 flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
                      <span className="flex items-center gap-1">
                        <Wind size={12} />
                        {formatWindSpeed(corridor.mean_wind_speed)}
                      </span>
                      <span className="flex items-center gap-1">
                        <ArrowRight size={12} />
                        {corridor.dominant_direction}
                        {corridor.wind_direction_deg != null && (
                          <span className="text-gray-400">
                            ({corridor.wind_direction_deg}°)
                          </span>
                        )}
                      </span>
                      <span
                        className="rounded px-1 py-0.5 text-xs"
                        style={{
                          backgroundColor:
                            RISK_COLORS[corridor.risk_level] + '20',
                          color: RISK_COLORS[corridor.risk_level],
                        }}
                      >
                        {RISK_LABELS[corridor.risk_level].zh}
                      </span>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <div className="card text-center text-sm text-gray-500">
              目前解析度下未偵測到風廊。
            </div>
          )}
        </div>

        {/* Map */}
        <div className="card h-[500px] overflow-hidden p-0 lg:col-span-2">
          <WindMap
            gridCells={gridCells}
            corridors={displayCorridors}
            height={height}
            onHeightChange={setHeight}
            layers={layers}
            onLayersChange={setLayers}
            isLoading={gridsLoading}
          />
        </div>
      </div>

      {/* Selected corridor detail */}
      {selectedCorridor && (
        <div className="card">
          <h3 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-200">
            風廊詳情: {selectedCorridor.name}
          </h3>
          <div className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-5">
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">類型</p>
              <p className="font-medium text-gray-800 dark:text-gray-100 capitalize">
                {selectedCorridor.type}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                平均風速
              </p>
              <p className="font-medium text-gray-800 dark:text-gray-100">
                {formatWindSpeed(selectedCorridor.mean_wind_speed)}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                主風向
              </p>
              <p className="font-medium text-gray-800 dark:text-gray-100">
                {selectedCorridor.dominant_direction}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                風向角度
              </p>
              <p className="font-medium text-gray-800 dark:text-gray-100">
                {selectedCorridor.wind_direction_deg != null
                  ? `${selectedCorridor.wind_direction_deg}°`
                  : '-'}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                風險等級
              </p>
              <p
                className="font-medium"
                style={{ color: RISK_COLORS[selectedCorridor.risk_level] }}
              >
                {RISK_LABELS[selectedCorridor.risk_level].zh} /{' '}
                {RISK_LABELS[selectedCorridor.risk_level].en}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
