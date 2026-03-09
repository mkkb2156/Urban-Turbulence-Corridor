import { useMemo } from 'react';
import type { WindRoseSector } from '../../api/types';
import { windSpeedColor } from '../../utils/colors';

interface WindRoseChartProps {
  data?: WindRoseSector[];
  size?: number;
  isLoading?: boolean;
}

const FULL_DIRECTIONS = [
  'N', 'NNE', 'NE', 'ENE',
  'E', 'ESE', 'SE', 'SSE',
  'S', 'SSW', 'SW', 'WSW',
  'W', 'WNW', 'NW', 'NNW',
];

// NE monsoon directions to highlight
const NE_MONSOON = new Set(['NNE', 'NE', 'ENE']);

export default function WindRoseChart({
  data,
  size = 300,
  isLoading,
}: WindRoseChartProps) {
  const center = size / 2;
  const maxRadius = size / 2 - 40;
  const sectorAngle = (2 * Math.PI) / 16;

  const maxFrequency = useMemo(
    () => (data ? Math.max(...data.map((d) => d.frequency), 1) : 1),
    [data],
  );

  // Generate sector paths
  const sectors = useMemo(() => {
    if (!data) return [];

    return data.map((sector) => {
      const angleIndex = FULL_DIRECTIONS.indexOf(sector.direction);
      if (angleIndex === -1) return null;

      // Rotate -90 degrees so N is at top
      const startAngle = angleIndex * sectorAngle - Math.PI / 2 - sectorAngle / 2;
      const endAngle = startAngle + sectorAngle;
      const radius = (sector.frequency / maxFrequency) * maxRadius;

      const x1 = center + Math.cos(startAngle) * radius;
      const y1 = center + Math.sin(startAngle) * radius;
      const x2 = center + Math.cos(endAngle) * radius;
      const y2 = center + Math.sin(endAngle) * radius;

      const largeArc = sectorAngle > Math.PI ? 1 : 0;

      const path = [
        `M ${center} ${center}`,
        `L ${x1} ${y1}`,
        `A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2}`,
        'Z',
      ].join(' ');

      const isNEMonsoon = NE_MONSOON.has(sector.direction);

      return {
        direction: sector.direction,
        path,
        color: windSpeedColor(sector.mean_speed),
        isNEMonsoon,
        frequency: sector.frequency,
        meanSpeed: sector.mean_speed,
      };
    }).filter(Boolean);
  }, [data, maxFrequency, center, maxRadius, sectorAngle]);

  // Concentric circles
  const circles = [0.25, 0.5, 0.75, 1.0].map((frac) => frac * maxRadius);

  // Direction labels
  const dirLabels = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
  const labelPositions = dirLabels.map((label, i) => {
    const angle = (i * Math.PI) / 4 - Math.PI / 2;
    const r = maxRadius + 20;
    return {
      label,
      x: center + Math.cos(angle) * r,
      y: center + Math.sin(angle) * r,
    };
  });

  if (isLoading) {
    return (
      <div
        className="flex items-center justify-center"
        style={{ width: size, height: size }}
      >
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="card">
      <h3 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-200">
        風花圖
      </h3>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="mx-auto"
      >
        {/* Concentric circles */}
        {circles.map((r, i) => (
          <circle
            key={i}
            cx={center}
            cy={center}
            r={r}
            fill="none"
            stroke="currentColor"
            strokeWidth={0.5}
            className="text-gray-300 dark:text-gray-600"
          />
        ))}

        {/* Cross lines */}
        {[0, 45, 90, 135].map((deg) => {
          const rad = (deg * Math.PI) / 180;
          return (
            <line
              key={deg}
              x1={center - Math.cos(rad) * maxRadius}
              y1={center - Math.sin(rad) * maxRadius}
              x2={center + Math.cos(rad) * maxRadius}
              y2={center + Math.sin(rad) * maxRadius}
              stroke="currentColor"
              strokeWidth={0.5}
              className="text-gray-300 dark:text-gray-600"
            />
          );
        })}

        {/* Sectors */}
        {sectors.map(
          (sector) =>
            sector && (
              <path
                key={sector.direction}
                d={sector.path}
                fill={sector.color}
                fillOpacity={0.75}
                stroke={sector.isNEMonsoon ? '#1e40af' : '#fff'}
                strokeWidth={sector.isNEMonsoon ? 2 : 0.5}
              >
                <title>
                  {sector.direction}: {(sector.frequency * 100).toFixed(1)}% |{' '}
                  {sector.meanSpeed.toFixed(1)} m/s
                </title>
              </path>
            ),
        )}

        {/* Direction labels */}
        {labelPositions.map(({ label, x, y }) => (
          <text
            key={label}
            x={x}
            y={y}
            textAnchor="middle"
            dominantBaseline="central"
            fontSize={11}
            fontWeight={NE_MONSOON.has(label) ? 700 : 500}
            className={
              NE_MONSOON.has(label)
                ? 'fill-blue-700 dark:fill-blue-400'
                : 'fill-gray-500 dark:fill-gray-400'
            }
          >
            {label}
          </text>
        ))}
      </svg>

      {/* Legend footnote */}
      <p className="mt-2 text-center text-xs text-gray-400 dark:text-gray-500">
        東北季風方向以藍色標示
      </p>
    </div>
  );
}
