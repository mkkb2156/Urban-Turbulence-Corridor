import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { useState } from 'react';
import clsx from 'clsx';
import type { RiskLevel } from '../../api/types';
import { RISK_COLORS, RISK_LABELS } from '../../utils/colors';

interface RiskDistributionProps {
  distribution?: Record<RiskLevel, number>;
  isLoading?: boolean;
}

type ChartType = 'pie' | 'bar';

const RISK_ORDER: RiskLevel[] = ['green', 'yellow', 'red', 'black'];

export default function RiskDistribution({
  distribution,
  isLoading,
}: RiskDistributionProps) {
  const [chartType, setChartType] = useState<ChartType>('pie');

  if (isLoading) {
    return (
      <div className="card flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
      </div>
    );
  }

  if (!distribution) return null;

  const data = RISK_ORDER.map((level) => ({
    name: `${RISK_LABELS[level].zh} (${RISK_LABELS[level].en})`,
    value: distribution[level] || 0,
    color: RISK_COLORS[level],
    level,
  }));

  const total = data.reduce((sum, d) => sum + d.value, 0);

  return (
    <div className="card">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200">
          風險分布
        </h3>
        <div className="flex gap-1">
          {(['pie', 'bar'] as ChartType[]).map((type) => (
            <button
              key={type}
              onClick={() => setChartType(type)}
              className={clsx(
                'rounded px-2 py-1 text-xs font-medium',
                chartType === type
                  ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300'
                  : 'text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700',
              )}
            >
              {type === 'pie' ? '圓餅圖' : '長條圖'}
            </button>
          ))}
        </div>
      </div>

      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          {chartType === 'pie' ? (
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={80}
                paddingAngle={2}
                dataKey="value"
                label={({ name, percent }) =>
                  percent > 0.05
                    ? `${name.split('(')[0].trim()} ${(percent * 100).toFixed(0)}%`
                    : ''
                }
                labelLine={false}
              >
                {data.map((entry) => (
                  <Cell key={entry.level} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value: number) => [
                  `${value} 格 (${total > 0 ? ((value / total) * 100).toFixed(1) : 0}%)`,
                  '數量',
                ]}
              />
            </PieChart>
          ) : (
            <BarChart data={data} layout="vertical">
              <XAxis type="number" />
              <YAxis dataKey="name" type="category" width={100} tick={{ fontSize: 11 }} />
              <Tooltip
                formatter={(value: number) => [
                  `${value} 格 (${total > 0 ? ((value / total) * 100).toFixed(1) : 0}%)`,
                  '數量',
                ]}
              />
              <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                {data.map((entry) => (
                  <Cell key={entry.level} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
