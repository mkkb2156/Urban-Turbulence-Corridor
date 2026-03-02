import { useState } from 'react';
import { BarChart3, Info } from 'lucide-react';
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import type { HeightOption, MapLayers } from '../api/types';
import { DEFAULT_MAP_LAYERS } from '../api/types';
import { useGridCells, useCorridors, useFAIData } from '../api/hooks';
import { faiColor } from '../utils/colors';
import WindMap from '../components/map/WindMap';

export default function FAIPage() {
  const [height, setHeight] = useState<HeightOption>(50);
  const [layers, setLayers] = useState<MapLayers>({
    ...DEFAULT_MAP_LAYERS,
    fai: true,
    risk: false,
  });

  const { data: gridCells, isLoading: gridsLoading } = useGridCells(height);
  const { data: corridors } = useCorridors();
  const { data: faiData, isLoading: faiLoading } = useFAIData(height);

  // Prepare scatter data: terrain roughness vs FAI
  const scatterData = faiData?.map((d) => ({
    x: d.terrain_roughness,
    y: d.fai_value,
    fill: faiColor(d.fai_value),
    gridId: d.grid_id,
    buildingDensity: d.building_density,
  }));

  return (
    <div className="space-y-6">
      <div>
        <h2 className="flex items-center gap-2 text-xl font-bold text-gray-900 dark:text-white">
          <BarChart3 size={24} className="text-blue-500" />
          Frontal Area Index (FAI) Analysis
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Building frontal area index visualization for wind turbulence estimation
        </p>
      </div>

      {/* Info card */}
      <div className="card flex items-start gap-3 bg-blue-50 dark:bg-blue-900/20">
        <Info size={18} className="mt-0.5 shrink-0 text-blue-500" />
        <div className="text-sm text-blue-800 dark:text-blue-200">
          <p className="font-medium">What is FAI?</p>
          <p className="mt-1 text-xs text-blue-600 dark:text-blue-300">
            The Frontal Area Index (FAI) measures the ratio of building frontal
            area to the total plan area. Higher FAI values indicate greater
            wind obstruction and turbulence potential. Values typically range
            from 0 (open terrain) to 2+ (dense urban core).
          </p>
        </div>
      </div>

      {/* Map */}
      <div className="card h-[450px] overflow-hidden p-0">
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

      {/* FAI scatter chart: terrain roughness vs FAI */}
      <div className="card">
        <h3 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-200">
          Terrain Roughness vs FAI
        </h3>
        {faiLoading ? (
          <div className="flex h-64 items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
          </div>
        ) : scatterData && scatterData.length > 0 ? (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  type="number"
                  dataKey="x"
                  name="Terrain Roughness"
                  label={{
                    value: 'Terrain Roughness',
                    position: 'bottom',
                    fontSize: 12,
                  }}
                />
                <YAxis
                  type="number"
                  dataKey="y"
                  name="FAI"
                  label={{
                    value: 'FAI',
                    angle: -90,
                    position: 'insideLeft',
                    fontSize: 12,
                  }}
                />
                <Tooltip
                  formatter={(value: number, name: string) => [
                    value.toFixed(3),
                    name === 'x' ? 'Terrain Roughness' : 'FAI',
                  ]}
                  labelFormatter={() => ''}
                />
                <Scatter data={scatterData}>
                  {scatterData.map((entry, index) => (
                    <Cell key={index} fill={entry.fill} />
                  ))}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="flex h-64 items-center justify-center text-sm text-gray-400">
            No FAI data available for the selected height.
          </div>
        )}
      </div>

      {/* FAI color scale legend */}
      <div className="card">
        <h3 className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-200">
          FAI Color Scale
        </h3>
        <div className="flex items-center gap-1">
          {Array.from({ length: 20 }).map((_, i) => {
            const val = (i / 19) * 2;
            return (
              <div
                key={i}
                className="h-4 flex-1 first:rounded-l last:rounded-r"
                style={{ backgroundColor: faiColor(val) }}
              />
            );
          })}
        </div>
        <div className="mt-1 flex justify-between text-xs text-gray-500 dark:text-gray-400">
          <span>0 (Open)</span>
          <span>1.0</span>
          <span>2.0+ (Dense)</span>
        </div>
      </div>
    </div>
  );
}
