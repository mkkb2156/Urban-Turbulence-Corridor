import { useEffect, useState, useCallback, useRef } from 'react';
import type maplibregl from 'maplibre-gl';
import chroma from 'chroma-js';
import apiClient from '../../api/client';
import type { RegionalWindResponse } from '../../api/types';

interface RegionalWindLayerProps {
  map: maplibregl.Map | null;
  visible: boolean;
  height?: number;
}

// ─── Configuration ─────────────────────────────────────────────
const ZOOM_THRESHOLD = 11;

const regionColorScale = chroma
  .scale(['#93c5fd', '#6ee7b7', '#fbbf24', '#f87171', '#7f1d1d'])
  .domain([0, 4, 8, 12, 18])
  .mode('lab');

const REGIONAL_ARROWS_SOURCE = 'regional-wind-arrows';
const REGIONAL_ARROWS_LAYER = 'regional-wind-arrows-layer';
const REGIONAL_RISK_SOURCE = 'regional-risk-dots';
const REGIONAL_RISK_LAYER = 'regional-risk-dots-layer';

export default function RegionalWindLayer({ map, visible, height = 10 }: RegionalWindLayerProps) {
  const [windData, setWindData] = useState<RegionalWindResponse | null>(null);
  const [isActive, setIsActive] = useState(false);
  const addedLayersRef = useRef(false);

  // Fetch regional wind data
  const fetchRegionalWind = useCallback(async () => {
    if (!map) return;
    const bounds = map.getBounds();
    const zoom = map.getZoom();

    if (zoom >= ZOOM_THRESHOLD) {
      setIsActive(false);
      return;
    }

    setIsActive(true);

    try {
      const data = await apiClient.get<RegionalWindResponse>('/wind/regional', {
        min_lon: bounds.getWest(),
        min_lat: bounds.getSouth(),
        max_lon: bounds.getEast(),
        max_lat: bounds.getNorth(),
        height,
        resolution: zoom < 8 ? 0.5 : zoom < 10 ? 0.2 : 0.1,
      });
      setWindData(data);
    } catch (err) {
      console.warn('Regional wind fetch failed:', err);
    }
  }, [map, height]);

  // Fetch on mount and when map moves
  useEffect(() => {
    if (!map || !visible) return;

    fetchRegionalWind();

    const onMoveEnd = () => {
      const zoom = map.getZoom();
      if (zoom < ZOOM_THRESHOLD) {
        fetchRegionalWind();
      } else {
        setIsActive(false);
      }
    };

    map.on('moveend', onMoveEnd);
    return () => { map.off('moveend', onMoveEnd); };
  }, [map, visible, fetchRegionalWind]);

  // Add vector layers for wind arrows and risk dots (NO canvas particles)
  useEffect(() => {
    if (!map || !windData || !isActive || !visible) return;

    const addLayers = () => {
      // Risk dots (colored circles at grid points)
      const riskFeatures: GeoJSON.Feature[] = windData.points.map((p) => ({
        type: 'Feature' as const,
        geometry: { type: 'Point' as const, coordinates: [p.lon, p.lat] },
        properties: {
          wind_speed: p.wind_speed,
          color: regionColorScale(Math.min(p.wind_speed, 18)).hex(),
          risk_level: p.risk_level,
        },
      }));

      if (!map.getSource(REGIONAL_RISK_SOURCE)) {
        map.addSource(REGIONAL_RISK_SOURCE, {
          type: 'geojson',
          data: { type: 'FeatureCollection', features: riskFeatures },
        });
      } else {
        (map.getSource(REGIONAL_RISK_SOURCE) as maplibregl.GeoJSONSource).setData({
          type: 'FeatureCollection',
          features: riskFeatures,
        });
      }

      if (!map.getLayer(REGIONAL_RISK_LAYER)) {
        map.addLayer({
          id: REGIONAL_RISK_LAYER,
          type: 'circle',
          source: REGIONAL_RISK_SOURCE,
          paint: {
            'circle-radius': [
              'interpolate', ['linear'], ['zoom'],
              6, 6,
              8, 10,
              10, 16,
            ],
            'circle-color': ['get', 'color'],
            'circle-opacity': 0.2,
            'circle-blur': 0.4,
          },
        });
      }

      // Wind arrow symbols
      const arrowFeatures: GeoJSON.Feature[] = windData.points.map((p) => ({
        type: 'Feature' as const,
        geometry: { type: 'Point' as const, coordinates: [p.lon, p.lat] },
        properties: {
          wind_speed: p.wind_speed,
          wind_direction: p.wind_direction,
          color: regionColorScale(Math.min(p.wind_speed, 18)).hex(),
          label: `${p.wind_speed} m/s`,
        },
      }));

      if (!map.getSource(REGIONAL_ARROWS_SOURCE)) {
        map.addSource(REGIONAL_ARROWS_SOURCE, {
          type: 'geojson',
          data: { type: 'FeatureCollection', features: arrowFeatures },
        });
      } else {
        (map.getSource(REGIONAL_ARROWS_SOURCE) as maplibregl.GeoJSONSource).setData({
          type: 'FeatureCollection',
          features: arrowFeatures,
        });
      }

      if (!map.getLayer(REGIONAL_ARROWS_LAYER)) {
        map.addLayer({
          id: REGIONAL_ARROWS_LAYER,
          type: 'symbol',
          source: REGIONAL_ARROWS_SOURCE,
          layout: {
            'text-field': '→',
            'text-size': [
              'interpolate', ['linear'], ['get', 'wind_speed'],
              0, 14,
              8, 22,
              15, 30,
            ],
            'text-rotate': ['get', 'wind_direction'],
            'text-allow-overlap': true,
            'text-ignore-placement': true,
          },
          paint: {
            'text-color': ['get', 'color'],
            'text-halo-color': 'rgba(0,0,0,0.3)',
            'text-halo-width': 1,
          },
        });
      }

      addedLayersRef.current = true;
    };

    if (map.isStyleLoaded()) {
      addLayers();
    }

    return () => {
      if (!addedLayersRef.current) return;
      for (const layerId of [REGIONAL_ARROWS_LAYER, REGIONAL_RISK_LAYER]) {
        if (map.getLayer(layerId)) map.removeLayer(layerId);
      }
      for (const sourceId of [REGIONAL_ARROWS_SOURCE, REGIONAL_RISK_SOURCE]) {
        if (map.getSource(sourceId)) map.removeSource(sourceId);
      }
      addedLayersRef.current = false;
    };
  }, [map, windData, isActive, visible]);

  return null;
}
