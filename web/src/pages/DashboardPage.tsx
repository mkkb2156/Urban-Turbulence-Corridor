import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plane, Navigation, Wind } from 'lucide-react';
import type { HeightOption, MapLayers } from '../api/types';
import { DEFAULT_MAP_LAYERS } from '../api/types';
import { useDashboardStats, useGridCells, useCorridors, useWindRose } from '../api/hooks';
import WindMap from '../components/map/WindMap';
import StatsCards from '../components/dashboard/StatsCards';
import WindRoseChart from '../components/dashboard/WindRoseChart';
import RiskDistribution from '../components/dashboard/RiskDistribution';

export default function DashboardPage() {
  const navigate = useNavigate();
  const [height, setHeight] = useState<HeightOption>(50);
  const [layers, setLayers] = useState<MapLayers>(DEFAULT_MAP_LAYERS);

  const { data: stats, isLoading: statsLoading } = useDashboardStats();
  const { data: gridCells, isLoading: gridsLoading } = useGridCells(height);
  const { data: corridors } = useCorridors();
  const { data: windRose, isLoading: windRoseLoading } = useWindRose();

  const quickActions = [
    {
      icon: Plane,
      title: '無人機適飛檢查',
      desc: '查詢任意座標的飛行風險與適飛性',
      color: 'bg-blue-500',
      onClick: () => navigate('/risk?tab=drone'),
    },
    {
      icon: Navigation,
      title: '飛行路線規劃',
      desc: '規劃最安全或最短的無人機飛行路線',
      color: 'bg-emerald-500',
      onClick: () => navigate('/analysis'),
    },
    {
      icon: Wind,
      title: '風廊總覽',
      desc: '檢視台北都會區已識別的風廊通道',
      color: 'bg-purple-500',
      onClick: () => navigate('/corridors'),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page title + wind summary */}
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">
            儀表板
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            台北都會區城市風廊總覽
          </p>
        </div>
        {stats && (
          <div className="rounded-md bg-blue-50 px-3 py-1.5 text-sm dark:bg-blue-900/30">
            <span className="text-gray-500 dark:text-gray-400">目前平均風速 </span>
            <span className="font-semibold text-blue-700 dark:text-blue-300">
              {stats.mean_wind_speed?.toFixed(1) ?? '—'} m/s
            </span>
          </div>
        )}
      </div>

      {/* Quick action cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {quickActions.map((action) => (
          <button
            key={action.title}
            onClick={action.onClick}
            className="card flex items-start gap-3 p-4 text-left transition-shadow hover:shadow-lg"
          >
            <div className={`${action.color} flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-white`}>
              <action.icon size={20} />
            </div>
            <div>
              <div className="text-sm font-semibold text-gray-800 dark:text-gray-100">
                {action.title}
              </div>
              <div className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
                {action.desc}
              </div>
            </div>
          </button>
        ))}
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
