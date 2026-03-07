import { useState } from 'react';
import { Wind, ArrowRight } from 'lucide-react';
import clsx from 'clsx';
import { useCorridors, useGridCells } from '../api/hooks';
import type { HeightOption, MapLayers, Corridor } from '../api/types';
import { DEFAULT_MAP_LAYERS } from '../api/types';
import { RISK_COLORS, RISK_LABELS, CORRIDOR_COLORS } from '../utils/colors';
import { formatWindSpeed } from '../utils/format';
import WindMap from '../components/map/WindMap';

export default function CorridorPage() {
  const [height, setHeight] = useState<HeightOption>(50);
  const [layers, setLayers] = useState<MapLayers>({
    ...DEFAULT_MAP_LAYERS,
    corridors: true,
  });
  const [selectedCorridor, setSelectedCorridor] = useState<Corridor | null>(null);

  const { data: corridors, isLoading: corridorsLoading } = useCorridors();
  const { data: gridCells, isLoading: gridsLoading } = useGridCells(height);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">
          風廊
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          已識別的城市風廊及其特性
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Corridor list */}
        <div className="space-y-3 lg:col-span-1">
          <h3 className="text-sm font-semibold text-gray-600 dark:text-gray-300">
            已偵測風廊
          </h3>

          {corridorsLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="card animate-pulse">
                  <div className="h-4 w-32 rounded bg-gray-200 dark:bg-gray-700" />
                  <div className="mt-2 h-3 w-24 rounded bg-gray-200 dark:bg-gray-700" />
                </div>
              ))}
            </div>
          ) : corridors && corridors.length > 0 ? (
            <ul className="space-y-2">
              {corridors.map((corridor) => (
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
            corridors={corridors}
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
          <div className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
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
