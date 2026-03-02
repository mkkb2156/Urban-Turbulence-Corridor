import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import clsx from 'clsx';
import type { HeightOption, MapLayers } from '../api/types';
import { DEFAULT_MAP_LAYERS } from '../api/types';
import { useGridCells, useCorridors } from '../api/hooks';
import WindMap from '../components/map/WindMap';
import RiskDistribution from '../components/dashboard/RiskDistribution';
import { useDashboardStats } from '../api/hooks';
import FlyabilityChecker from '../components/drone/FlyabilityChecker';

type Tab = 'map' | 'drone';

export default function RiskPage() {
  const [searchParams] = useSearchParams();
  const initialTab = searchParams.get('tab') === 'drone' ? 'drone' : 'map';

  const [tab, setTab] = useState<Tab>(initialTab);
  const [height, setHeight] = useState<HeightOption>(50);
  const [layers, setLayers] = useState<MapLayers>(DEFAULT_MAP_LAYERS);

  const { data: gridCells, isLoading: gridsLoading } = useGridCells(height);
  const { data: corridors } = useCorridors();
  const { data: stats, isLoading: statsLoading } = useDashboardStats();

  const tabs: { id: Tab; label: string }[] = [
    { id: 'map', label: 'Risk Map' },
    { id: 'drone', label: 'Drone Check' },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">
          Risk Assessment
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Evaluate wind risk levels and check drone flyability
        </p>
      </div>

      {/* Tab navigation */}
      <div className="flex gap-1 border-b border-gray-200 dark:border-gray-700">
        {tabs.map(({ id, label }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={clsx(
              '-mb-px border-b-2 px-4 py-2.5 text-sm font-medium transition-colors',
              tab === id
                ? 'border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400'
                : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 dark:text-gray-400',
            )}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === 'map' && (
        <div className="space-y-6">
          <div className="card h-[500px] overflow-hidden p-0">
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

          <div className="max-w-md">
            <RiskDistribution
              distribution={stats?.risk_distribution}
              isLoading={statsLoading}
            />
          </div>
        </div>
      )}

      {tab === 'drone' && <FlyabilityChecker />}
    </div>
  );
}
