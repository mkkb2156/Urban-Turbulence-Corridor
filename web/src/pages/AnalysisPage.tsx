import { useState, useRef, useEffect, useCallback } from 'react';
import maplibregl from 'maplibre-gl';
import clsx from 'clsx';
import { Route, Pentagon, Navigation, Loader2, ChevronUp, ChevronDown } from 'lucide-react';
import { DEFAULT_CENTER, DEFAULT_ZOOM } from '../utils/geo';
import { RISK_COLORS } from '../utils/colors';
import { formatWindSpeed } from '../utils/format';
import { useFlight } from '../contexts/FlightContext';
import { useForecast, useAreaPrediction, useRouteAnalysis, useRoutePlan } from '../api/hooks';
import type { AreaPredictResponse, RouteAnalyzeResponse, RoutePlanResponse, RiskLevel } from '../api/types';
import DroneSelector from '../components/drone/DroneSelector';
import TimelinePlayer from '../components/timeline/TimelinePlayer';
import type { DrawMode } from '../components/map/DrawingToolbar';
import DrawingToolbar from '../components/map/DrawingToolbar';

type AnalysisTab = 'area' | 'route' | 'plan';

const ROUTE_COLORS: Record<string, string> = {
  safest: '#2ecc71',
  shortest: '#e74c3c',
  balanced: '#3b82f6',
};

export default function AnalysisPage() {
  const { selectedDrone, setDrone, selectedHeight, setHeight } = useFlight();
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);

  const [tab, setTab] = useState<AnalysisTab>('area');
  const [drawMode, setDrawMode] = useState<DrawMode>('none');
  const [drawnPoints, setDrawnPoints] = useState<[number, number][]>([]);
  const [markers, setMarkers] = useState<maplibregl.Marker[]>([]);
  const [timelineIndex, setTimelineIndex] = useState(0);
  const [mobilePanel, setMobilePanel] = useState(false);

  // API hooks
  const { data: forecastData } = useForecast('taipei', 72);
  const areaMutation = useAreaPrediction();
  const routeMutation = useRouteAnalysis();
  const planMutation = useRoutePlan();

  const [areaResult, setAreaResult] = useState<AreaPredictResponse | null>(null);
  const [routeResult, setRouteResult] = useState<RouteAnalyzeResponse | null>(null);
  const [planResult, setPlanResult] = useState<RoutePlanResponse | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  // Initialize map
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: {
        version: 8,
        glyphs: 'https://fonts.openmaptiles.org/{fontstack}/{range}.pbf',
        sources: {
          'osm-tiles': {
            type: 'raster',
            tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
            tileSize: 256,
            attribution: '&copy; OpenStreetMap contributors',
          },
        },
        layers: [{
          id: 'osm-tiles', type: 'raster', source: 'osm-tiles', minzoom: 0, maxzoom: 19,
        }],
      },
      center: DEFAULT_CENTER,
      zoom: DEFAULT_ZOOM,
    });

    map.addControl(new maplibregl.NavigationControl(), 'top-right');
    map.addControl(new maplibregl.ScaleControl({ maxWidth: 200 }), 'bottom-right');

    map.on('load', () => {
      // Drawing polygon source
      map.addSource('draw-polygon', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      });
      map.addLayer({
        id: 'draw-polygon-fill', type: 'fill', source: 'draw-polygon',
        paint: { 'fill-color': '#3b82f6', 'fill-opacity': 0.15 },
      });
      map.addLayer({
        id: 'draw-polygon-line', type: 'line', source: 'draw-polygon',
        paint: { 'line-color': '#3b82f6', 'line-width': 2 },
      });

      // Drawing route source
      map.addSource('draw-route', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      });
      map.addLayer({
        id: 'draw-route-line', type: 'line', source: 'draw-route',
        paint: { 'line-color': '#f59e0b', 'line-width': 3 },
        layout: { 'line-cap': 'round', 'line-join': 'round' },
      });

      // Result layers
      map.addSource('result-cells', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      });
      map.addLayer({
        id: 'result-cells-fill', type: 'fill', source: 'result-cells',
        paint: { 'fill-color': ['get', 'color'], 'fill-opacity': 0.5 },
      });

      // Plan routes source
      for (const mode of ['safest', 'shortest', 'balanced']) {
        map.addSource(`route-${mode}`, {
          type: 'geojson',
          data: { type: 'FeatureCollection', features: [] },
        });
        map.addLayer({
          id: `route-${mode}-line`, type: 'line', source: `route-${mode}`,
          paint: {
            'line-color': ROUTE_COLORS[mode],
            'line-width': mode === 'balanced' ? 4 : 3,
            'line-opacity': 0.8,
            'line-dasharray': mode === 'safest' ? [4, 2] : mode === 'shortest' ? [2, 2] : [1],
          },
          layout: { 'line-cap': 'round', 'line-join': 'round' },
        });
      }

      // Route analysis colored segments
      map.addSource('route-analysis', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      });
      map.addLayer({
        id: 'route-analysis-line', type: 'line', source: 'route-analysis',
        paint: {
          'line-color': ['get', 'color'],
          'line-width': 5,
          'line-opacity': 0.85,
        },
        layout: { 'line-cap': 'round', 'line-join': 'round' },
      });
    });

    mapRef.current = map;
    return () => { map.remove(); mapRef.current = null; };
  }, []);

  // Map click handler for drawing
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const handleClick = (e: maplibregl.MapMouseEvent) => {
      if (drawMode === 'none') return;
      const pt: [number, number] = [e.lngLat.lng, e.lngLat.lat];

      setDrawnPoints((prev) => {
        const next = [...prev, pt];
        return next;
      });

      // Add marker
      const marker = new maplibregl.Marker({ color: drawMode === 'polygon' ? '#3b82f6' : '#f59e0b' })
        .setLngLat(pt)
        .addTo(map);
      setMarkers((prev) => [...prev, marker]);
    };

    map.on('click', handleClick);
    return () => { map.off('click', handleClick); };
  }, [drawMode]);

  // Update drawn shapes on map
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    const polygonSrc = map.getSource('draw-polygon') as maplibregl.GeoJSONSource | undefined;
    const routeSrc = map.getSource('draw-route') as maplibregl.GeoJSONSource | undefined;

    if (drawMode === 'polygon' && drawnPoints.length >= 3 && polygonSrc) {
      const closed = [...drawnPoints, drawnPoints[0]];
      polygonSrc.setData({
        type: 'FeatureCollection',
        features: [{
          type: 'Feature', geometry: { type: 'Polygon', coordinates: [closed] }, properties: {},
        }],
      });
    } else if (polygonSrc) {
      polygonSrc.setData({ type: 'FeatureCollection', features: [] });
    }

    if ((drawMode === 'route' || drawMode === 'point') && drawnPoints.length >= 2 && routeSrc) {
      routeSrc.setData({
        type: 'FeatureCollection',
        features: [{
          type: 'Feature', geometry: { type: 'LineString', coordinates: drawnPoints }, properties: {},
        }],
      });
    } else if (routeSrc) {
      routeSrc.setData({ type: 'FeatureCollection', features: [] });
    }
  }, [drawnPoints, drawMode]);

  // Update cursor
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    map.getCanvas().style.cursor = drawMode !== 'none' ? 'crosshair' : '';
  }, [drawMode]);

  const clearDrawing = useCallback(() => {
    setDrawnPoints([]);
    markers.forEach((m) => m.remove());
    setMarkers([]);
    setAreaResult(null);
    setRouteResult(null);
    setPlanResult(null);

    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;
    const sources = ['draw-polygon', 'draw-route', 'result-cells', 'route-analysis', 'route-safest', 'route-shortest', 'route-balanced'];
    for (const id of sources) {
      const src = map.getSource(id) as maplibregl.GeoJSONSource | undefined;
      if (src) src.setData({ type: 'FeatureCollection', features: [] });
    }
  }, [markers]);

  const undoPoint = useCallback(() => {
    setDrawnPoints((prev) => prev.slice(0, -1));
    const last = markers[markers.length - 1];
    if (last) last.remove();
    setMarkers((prev) => prev.slice(0, -1));
  }, [markers]);

  // Submit analysis
  const handleAnalyze = useCallback(async () => {
    setAnalysisError(null);

    try {
      if (tab === 'area' && drawnPoints.length >= 3) {
        const result = await areaMutation.mutateAsync({
          polygon: drawnPoints,
          height: selectedHeight,
          drone_id: selectedDrone?.id,
        });
        setAreaResult(result);

        // Show result cells on map
        const map = mapRef.current;
        if (map && map.isStyleLoaded()) {
          const src = map.getSource('result-cells') as maplibregl.GeoJSONSource | undefined;
          if (src && result.grid_cells) {
            const features: GeoJSON.Feature[] = result.grid_cells.map((c) => ({
              type: 'Feature' as const,
              geometry: {
                type: 'Polygon' as const,
                coordinates: [[
                  [c.lon - 0.0025, c.lat - 0.0025],
                  [c.lon + 0.0025, c.lat - 0.0025],
                  [c.lon + 0.0025, c.lat + 0.0025],
                  [c.lon - 0.0025, c.lat + 0.0025],
                  [c.lon - 0.0025, c.lat - 0.0025],
                ]],
              },
              properties: { color: RISK_COLORS[c.risk_level as RiskLevel] },
            }));
            src.setData({ type: 'FeatureCollection', features });
          }
        }
      } else if (tab === 'route' && drawnPoints.length >= 2) {
        const result = await routeMutation.mutateAsync({
          waypoints: drawnPoints,
          height: selectedHeight,
          drone_id: selectedDrone?.id,
        });
        setRouteResult(result);

        // Show colored route segments on map
        const map = mapRef.current;
        if (map && map.isStyleLoaded() && result.segments?.length) {
          const src = map.getSource('route-analysis') as maplibregl.GeoJSONSource | undefined;
          if (src) {
            const features: GeoJSON.Feature[] = result.segments
              .filter((seg) => seg.sample_points?.length >= 2)
              .map((seg) => ({
                type: 'Feature' as const,
                geometry: {
                  type: 'LineString' as const,
                  coordinates: seg.sample_points.map((p) => [p.lon, p.lat]),
                },
                properties: { color: RISK_COLORS[seg.risk_level as RiskLevel] },
              }));
            src.setData({ type: 'FeatureCollection', features });
          }
        }
      } else if (tab === 'plan' && drawnPoints.length >= 2) {
        const result = await planMutation.mutateAsync({
          start: drawnPoints[0],
          end: drawnPoints[drawnPoints.length - 1],
          height: selectedHeight,
          drone_id: selectedDrone?.id,
          mode: 'balanced',
        });
        setPlanResult(result);

        // Show 3 routes on map
        const map = mapRef.current;
        if (map && map.isStyleLoaded()) {
          for (const route of result.routes) {
            const src = map.getSource(`route-${route.mode}`) as maplibregl.GeoJSONSource | undefined;
            if (src) {
              src.setData({
                type: 'FeatureCollection',
                features: [{
                  type: 'Feature',
                  geometry: route.geometry,
                  properties: {},
                }],
              });
            }
          }
        }
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : '分析失敗，請稍後再試';
      setAnalysisError(message);
      console.error('Analysis failed:', err);
    }
  }, [tab, drawnPoints, selectedHeight, selectedDrone, areaMutation, routeMutation, planMutation]);

  const isLoading = areaMutation.isPending || routeMutation.isPending || planMutation.isPending;

  const tabs: { id: AnalysisTab; icon: typeof Pentagon; label: string; drawHint: string }[] = [
    { id: 'area', icon: Pentagon, label: '區域分析', drawHint: '繪製多邊形（點擊 3+ 個點）' },
    { id: 'route', icon: Route, label: '路線查詢', drawHint: '繪製路線（點擊 2+ 個點）' },
    { id: 'plan', icon: Navigation, label: '路線規劃', drawHint: '設定起點與終點' },
  ];

  const activeTab = tabs.find((t) => t.id === tab)!;

  return (
    <div className="relative flex h-[calc(100vh-5rem)] flex-col gap-4 md:h-[calc(100vh-8rem)] md:flex-row">
      {/* Mobile toggle button */}
      <button
        onClick={() => setMobilePanel(!mobilePanel)}
        className="fixed bottom-20 right-3 z-30 flex items-center gap-1 rounded-full bg-blue-600 px-3 py-2 text-xs font-medium text-white shadow-lg md:hidden"
      >
        {mobilePanel ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
        {mobilePanel ? '地圖' : '面板'}
      </button>

      {/* Left sidebar / Mobile bottom sheet */}
      <div className={clsx(
        // Mobile: bottom sheet overlay
        'max-md:fixed max-md:inset-x-0 max-md:bottom-0 max-md:z-20 max-md:max-h-[70vh] max-md:overflow-y-auto max-md:rounded-t-2xl max-md:bg-white max-md:shadow-2xl max-md:transition-transform max-md:duration-300 max-md:dark:bg-gray-900',
        !mobilePanel && 'max-md:translate-y-full',
        // Desktop: fixed sidebar
        'md:flex md:w-80 md:flex-shrink-0 md:flex-col md:gap-3 md:overflow-y-auto',
      )}>
        {/* Mobile drag handle */}
        <div className="flex justify-center py-2 md:hidden">
          <div className="h-1 w-8 rounded-full bg-gray-300 dark:bg-gray-600" />
        </div>
        <div className="flex flex-col gap-3 p-3 md:p-0">
        {/* Tab selector */}
        <div className="flex gap-1 rounded-lg bg-gray-100 p-1 dark:bg-gray-800">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => {
                setTab(t.id);
                clearDrawing();
                setAnalysisError(null);
                // Auto-set draw mode for selected tab
                const modeMap: Record<AnalysisTab, DrawMode> = { area: 'polygon', route: 'route', plan: 'point' };
                setDrawMode(modeMap[t.id]);
              }}
              className={clsx(
                'flex flex-1 items-center justify-center gap-1.5 rounded-md px-2 py-2 text-xs font-medium transition-colors',
                tab === t.id ? 'bg-white text-blue-600 shadow dark:bg-gray-700 dark:text-blue-400' : 'text-gray-500 hover:text-gray-700',
              )}
            >
              <t.icon size={14} />
              {t.label}
            </button>
          ))}
        </div>

        {/* Drone selector */}
        <DroneSelector selected={selectedDrone} onSelect={setDrone} compact />

        {/* Height selector */}
        <div className="flex items-center gap-2 rounded-md bg-white px-3 py-2 shadow-md dark:bg-gray-800">
          <span className="text-xs font-medium text-gray-500">高度</span>
          <div className="flex gap-1">
            {([50, 80, 120] as const).map((h) => (
              <button
                key={h}
                onClick={() => setHeight(h)}
                className={clsx(
                  'rounded px-2 py-1 text-xs font-medium',
                  selectedHeight === h ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300',
                )}
              >
                {h}m
              </button>
            ))}
          </div>
        </div>

        {/* Drawing hint */}
        <div className="rounded-md border border-blue-200 bg-blue-50 px-3 py-2 text-xs text-blue-700 dark:border-blue-800 dark:bg-blue-900/20 dark:text-blue-300">
          {activeTab.drawHint}
          {drawnPoints.length > 0 && (
            <span className="ml-1 font-medium">({drawnPoints.length} 個點)</span>
          )}
        </div>

        {/* Analyze button */}
        <button
          onClick={handleAnalyze}
          disabled={isLoading || drawnPoints.length < (tab === 'area' ? 3 : 2)}
          className="flex items-center justify-center gap-2 rounded-md bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isLoading ? <Loader2 size={16} className="animate-spin" /> : <Navigation size={16} />}
          {tab === 'area' ? '分析區域' : tab === 'route' ? '分析路線' : '規劃路線'}
        </button>

        {/* Error display */}
        {analysisError && (
          <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
            {analysisError}
          </div>
        )}

        {/* Results panel */}
        {areaResult && tab === 'area' && (
          <div className="space-y-3 rounded-lg bg-white p-4 shadow dark:bg-gray-800">
            <h3 className="text-sm font-bold text-gray-800 dark:text-white">區域分析</h3>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="rounded bg-gray-50 p-2 dark:bg-gray-700">
                <div className="text-gray-500">面積</div>
                <div className="font-bold">{areaResult.area_km2} km²</div>
              </div>
              <div className="rounded bg-gray-50 p-2 dark:bg-gray-700">
                <div className="text-gray-500">網格數</div>
                <div className="font-bold">{areaResult.grid_count}</div>
              </div>
              <div className="rounded bg-gray-50 p-2 dark:bg-gray-700">
                <div className="text-gray-500">平均風速</div>
                <div className="font-bold">{formatWindSpeed(areaResult.wind_stats.mean_speed)}</div>
              </div>
              <div className="rounded bg-gray-50 p-2 dark:bg-gray-700">
                <div className="text-gray-500">最大風速</div>
                <div className="font-bold">{formatWindSpeed(areaResult.wind_stats.max_speed)}</div>
              </div>
            </div>
            {/* Risk distribution bars */}
            <div className="space-y-1">
              <div className="text-xs font-medium text-gray-500">風險分布</div>
              {(['green', 'yellow', 'red', 'black'] as const).map((level) => (
                <div key={level} className="flex items-center gap-2 text-xs">
                  <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: RISK_COLORS[level] }} />
                  <div className="flex-1">
                    <div className="h-2 rounded-full bg-gray-100 dark:bg-gray-700">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${areaResult.risk_distribution[level] || 0}%`,
                          backgroundColor: RISK_COLORS[level],
                        }}
                      />
                    </div>
                  </div>
                  <span className="w-10 text-right text-gray-500">{areaResult.risk_distribution[level] || 0}%</span>
                </div>
              ))}
            </div>
            {areaResult.flyability && (
              <div className={clsx(
                'rounded-md border p-2 text-xs',
                areaResult.flyability.flyable
                  ? 'border-green-200 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-900/20 dark:text-green-300'
                  : 'border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300',
              )}>
                {areaResult.flyability.flyable ? '可安全飛行' : '風險超過無人機耐受值'} &middot;
                安全區域: {areaResult.flyability.safe_percentage}%
              </div>
            )}
          </div>
        )}

        {routeResult && tab === 'route' && (
          <div className="space-y-3 rounded-lg bg-white p-4 shadow dark:bg-gray-800">
            <h3 className="text-sm font-bold text-gray-800 dark:text-white">路線分析</h3>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="rounded bg-gray-50 p-2 dark:bg-gray-700">
                <div className="text-gray-500">距離</div>
                <div className="font-bold">{(routeResult.total_distance_m / 1000).toFixed(1)} km</div>
              </div>
              <div className="rounded bg-gray-50 p-2 dark:bg-gray-700">
                <div className="text-gray-500">預估時間</div>
                <div className="font-bold">{Math.ceil(routeResult.total_time_s / 60)} min</div>
              </div>
              <div className="rounded bg-gray-50 p-2 dark:bg-gray-700">
                <div className="text-gray-500">平均風速</div>
                <div className="font-bold">{formatWindSpeed(routeResult.avg_wind_speed)}</div>
              </div>
              <div className="rounded bg-gray-50 p-2 dark:bg-gray-700">
                <div className="text-gray-500">最高風險</div>
                <div className="font-bold flex items-center gap-1">
                  <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: RISK_COLORS[routeResult.max_risk] }} />
                  {routeResult.max_risk}
                </div>
              </div>
            </div>
            {/* Segments table */}
            <div className="max-h-48 overflow-y-auto">
              <table className="w-full text-xs">
                <thead className="text-gray-400">
                  <tr><th className="text-left">段</th><th>風速</th><th>逆風</th><th>側風</th><th>風效</th><th>風險</th></tr>
                </thead>
                <tbody>
                  {routeResult.segments.map((seg, i) => (
                    <tr key={i} className="border-t border-gray-100 dark:border-gray-700">
                      <td className="py-1">{i + 1}</td>
                      <td className="text-center">{seg.avg_wind_speed} m/s</td>
                      <td className="text-center">{seg.headwind > 0 ? '+' : ''}{seg.headwind} m/s</td>
                      <td className="text-center">{Math.abs(seg.crosswind).toFixed(1)} m/s</td>
                      <td className="text-center">{seg.wind_effect_pct > 0 ? '+' : ''}{seg.wind_effect_pct}%</td>
                      <td className="text-center">
                        <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: RISK_COLORS[seg.risk_level as RiskLevel] }} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {planResult && tab === 'plan' && (
          <div className="space-y-3 rounded-lg bg-white p-4 shadow dark:bg-gray-800">
            <h3 className="text-sm font-bold text-gray-800 dark:text-white">路線比較</h3>
            {planResult.routes.map((route) => (
              <div
                key={route.mode}
                className="rounded-md border p-2 text-xs"
                style={{ borderColor: ROUTE_COLORS[route.mode] + '80' }}
              >
                <div className="flex items-center gap-2">
                  <span className="inline-block h-3 w-3 rounded" style={{ backgroundColor: ROUTE_COLORS[route.mode] }} />
                  <span className="font-bold capitalize">{route.mode}</span>
                  {route.mode === planResult.recommended && (
                    <span className="rounded bg-blue-100 px-1.5 py-0.5 text-[10px] font-medium text-blue-700 dark:bg-blue-900 dark:text-blue-300">
                      推薦
                    </span>
                  )}
                </div>
                <div className="mt-1 flex gap-3 text-gray-500">
                  <span>{(route.total_distance_m / 1000).toFixed(1)} km</span>
                  <span>{Math.ceil(route.total_time_s / 60)} min</span>
                  <span className="flex items-center gap-1">
                    <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: RISK_COLORS[route.max_risk] }} />
                    {route.max_risk}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
        </div>
      </div>

      {/* Map */}
      <div className="relative min-h-0 flex-1 overflow-hidden rounded-lg shadow-lg max-md:order-first">
        <div ref={containerRef} className="h-full w-full" />

        {/* Drawing toolbar */}
        <div className="absolute left-3 top-3 z-10">
          <DrawingToolbar
            mode={drawMode}
            onModeChange={(m) => { setDrawMode(m); if (m !== 'none') clearDrawing(); }}
            onClear={clearDrawing}
            onUndo={undoPoint}
            hasDrawing={drawnPoints.length > 0}
          />
        </div>

        {/* Timeline player */}
        {forecastData && (
          <div className="absolute bottom-2 left-2 right-2 z-10 md:bottom-4 md:left-4 md:right-4">
            <TimelinePlayer
              forecasts={forecastData.forecasts}
              currentIndex={timelineIndex}
              onIndexChange={setTimelineIndex}
            />
          </div>
        )}
      </div>
    </div>
  );
}
