import { useState } from 'react';
import type { HeightOption, MapLayers } from '../api/types';
import { DEFAULT_MAP_LAYERS } from '../api/types';
import { useDashboardStats, useGridCells, useCorridors, useWindRose } from '../api/hooks';
import WindMap from '../components/map/WindMap';
import StatsCards from '../components/dashboard/StatsCards';
import WindRoseChart from '../components/dashboard/WindRoseChart';
import RiskDistribution from '../components/dashboard/RiskDistribution';

export default function DashboardPage() {
  const [height, setHeight] = useState<HeightOption>(50);
  const [layers, setLayers] = useState<MapLayers>(DEFAULT_MAP_LAYERS);

  const { data: stats, isLoading: statsLoading } = useDashboardStats();
  const { data: gridCells, isLoading: gridsLoading } = useGridCells(height);
  const { data: corridors } = useCorridors();
  const { data: windRose, isLoading: windRoseLoading } = useWindRose();

  return (
    <div className="space-y-6">
      {/* Page title */}
      <div>
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">
          Dashboard
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Urban wind corridor overview for Taipei metropolitan area
        </p>
      </div>

      {/* Stats cards */}
      <StatsCards stats={stats} isLoading={statsLoading} />

      {/* Map */}
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

      {/* Charts row */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <WindRoseChart data={windRose} isLoading={windRoseLoading} />
        <RiskDistribution
          distribution={stats?.risk_distribution}
          isLoading={statsLoading}
        />
      </div>
    </div>
  );
}
