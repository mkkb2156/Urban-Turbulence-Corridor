import type { LucideIcon } from 'lucide-react';
import { Wind, Grid3x3, Route, Activity } from 'lucide-react';
import clsx from 'clsx';
import type { DashboardStats } from '../../api/types';
import { formatWindSpeed, abbreviateNumber, formatRelativeTime } from '../../utils/format';

interface StatsCardsProps {
  stats?: DashboardStats;
  isLoading?: boolean;
}

interface StatCardData {
  label: string;
  value: string;
  subtext?: string;
  icon: LucideIcon;
  color: string;
}

function Skeleton() {
  return (
    <div className="animate-pulse">
      <div className="mb-2 h-4 w-24 rounded bg-gray-200 dark:bg-gray-700" />
      <div className="h-8 w-16 rounded bg-gray-200 dark:bg-gray-700" />
    </div>
  );
}

export default function StatsCards({ stats, isLoading }: StatsCardsProps) {
  const cards: StatCardData[] = stats
    ? [
        {
          label: '網格數',
          value: abbreviateNumber(stats.total_grids),
          subtext: `監測面積 ${stats.monitoring_area_km2.toFixed(1)} km\u00B2`,
          icon: Grid3x3,
          color: 'text-blue-500',
        },
        {
          label: '平均風速',
          value: formatWindSpeed(stats.mean_wind_speed),
          icon: Wind,
          color: 'text-teal-500',
        },
        {
          label: '風廊數量',
          value: String(stats.corridor_count),
          subtext: '台北都會區已識別風廊',
          icon: Route,
          color: 'text-purple-500',
        },
        {
          label: '最後更新',
          value: formatRelativeTime(stats.last_updated),
          icon: Activity,
          color: 'text-orange-500',
        },
      ]
    : [];

  return (
    <div
      className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4"
      data-testid="stats-cards"
    >
      {isLoading
        ? Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="card">
              <Skeleton />
            </div>
          ))
        : cards.map((card) => (
            <div key={card.label} className="card" data-testid={`stat-card-${card.label}`}>
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
                    {card.label}
                  </p>
                  <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">
                    {card.value}
                  </p>
                  {card.subtext && (
                    <p className="mt-0.5 text-xs text-gray-400 dark:text-gray-500">
                      {card.subtext}
                    </p>
                  )}
                </div>
                <card.icon
                  size={24}
                  className={clsx('shrink-0', card.color)}
                />
              </div>
            </div>
          ))}
    </div>
  );
}
