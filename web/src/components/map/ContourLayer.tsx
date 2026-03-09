import { useEffect, useRef, useMemo } from 'react';
import type maplibregl from 'maplibre-gl';
import { point, featureCollection } from '@turf/helpers';
import interpolate from '@turf/interpolate';
import isolines from '@turf/isolines';
import type { GridCell } from '../../api/types';
import type { MapColorMode } from '../../utils/colors';
import { colorForValue, COLOR_MODE_RANGES } from '../../utils/colors';

interface ContourLayerProps {
  map: maplibregl.Map | null;
  gridCells?: GridCell[];
  visible: boolean;
  colorMode: MapColorMode;
  /** Number of contour levels to generate */
  levels?: number;
}

const HEATMAP_SOURCE = 'contour-heatmap';
const HEATMAP_LAYER = 'contour-heatmap-layer';
const CONTOUR_LINE_SOURCE = 'contour-lines';
const CONTOUR_LINE_LAYER = 'contour-lines-layer';
const CONTOUR_LABEL_LAYER = 'contour-labels-layer';

function getCellValue(cell: GridCell, mode: MapColorMode): number | null {
  switch (mode) {
    case 'wind_speed':
      return cell.wind_speed;
    case 'turbulence':
      return cell.turbulence ?? null;
    case 'gust_factor':
      return cell.gust_factor ?? null;
    case 'shelter':
      return cell.shelter_index ?? null;
    case 'risk':
    default:
      return cell.risk_score;
  }
}

function generateBreaks(mode: MapColorMode, levels: number): number[] {
  const range = COLOR_MODE_RANGES[mode];
  const breaks: number[] = [];
  const step = (range.max - range.min) / (levels + 1);
  for (let i = 1; i <= levels; i++) {
    breaks.push(range.min + step * i);
  }
  return breaks;
}

/**
 * Heatmap color ramp per color mode.
 * MapLibre heatmap-color uses density 0..1.
 */
function getHeatmapColorExpr(mode: MapColorMode): maplibregl.ExpressionSpecification {
  switch (mode) {
    case 'wind_speed':
      return [
        'interpolate', ['linear'], ['heatmap-density'],
        0, 'rgba(0,0,0,0)',
        0.1, 'rgba(96,165,250,0.4)',
        0.3, 'rgba(52,211,153,0.5)',
        0.5, 'rgba(251,191,36,0.5)',
        0.7, 'rgba(248,113,113,0.5)',
        1.0, 'rgba(153,27,27,0.6)',
      ];
    case 'turbulence':
      return [
        'interpolate', ['linear'], ['heatmap-density'],
        0, 'rgba(0,0,0,0)',
        0.2, 'rgba(147,197,253,0.3)',
        0.4, 'rgba(110,231,183,0.4)',
        0.6, 'rgba(251,191,36,0.5)',
        0.8, 'rgba(248,113,113,0.5)',
        1.0, 'rgba(127,29,29,0.6)',
      ];
    case 'gust_factor':
      return [
        'interpolate', ['linear'], ['heatmap-density'],
        0, 'rgba(0,0,0,0)',
        0.2, 'rgba(147,197,253,0.3)',
        0.5, 'rgba(251,191,36,0.4)',
        0.8, 'rgba(248,113,113,0.5)',
        1.0, 'rgba(127,29,29,0.6)',
      ];
    case 'shelter':
      return [
        'interpolate', ['linear'], ['heatmap-density'],
        0, 'rgba(0,0,0,0)',
        0.2, 'rgba(110,231,183,0.3)',
        0.5, 'rgba(251,191,36,0.4)',
        0.8, 'rgba(239,68,68,0.5)',
        1.0, 'rgba(127,29,29,0.6)',
      ];
    case 'risk':
    default:
      return [
        'interpolate', ['linear'], ['heatmap-density'],
        0, 'rgba(0,0,0,0)',
        0.15, 'rgba(46,204,113,0.3)',
        0.35, 'rgba(241,196,15,0.4)',
        0.6, 'rgba(231,76,60,0.5)',
        0.85, 'rgba(44,62,80,0.6)',
        1.0, 'rgba(30,30,30,0.7)',
      ];
  }
}

export default function ContourLayer({
  map,
  gridCells,
  visible,
  colorMode,
  levels = 5,
}: ContourLayerProps) {
  const addedRef = useRef(false);

  // Build point GeoJSON for heatmap from grid cells
  const heatmapGeoJSON = useMemo<GeoJSON.FeatureCollection>(() => {
    if (!gridCells?.length) return { type: 'FeatureCollection', features: [] };

    const range = COLOR_MODE_RANGES[colorMode];
    const features: GeoJSON.Feature[] = [];
    for (const cell of gridCells) {
      const value = getCellValue(cell, colorMode);
      if (value == null) continue;
      const weight = Math.max(0, Math.min(1, (value - range.min) / (range.max - range.min)));
      features.push({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [cell.lon, cell.lat] },
        properties: { value, weight },
      });
    }
    return { type: 'FeatureCollection', features };
  }, [gridCells, colorMode]);

  // Compute contour isolines
  const contourGeoJSON = useMemo<GeoJSON.FeatureCollection>(() => {
    if (!gridCells?.length) return { type: 'FeatureCollection', features: [] };

    const points = gridCells
      .map((cell) => {
        const value = getCellValue(cell, colorMode);
        if (value == null) return null;
        return point([cell.lon, cell.lat], { value });
      })
      .filter((p): p is NonNullable<typeof p> => p !== null);

    if (points.length < 3) return { type: 'FeatureCollection', features: [] };

    const pointCollection = featureCollection(points);

    // Coarser grid (1.0 km) to avoid excessive points
    const interpolated = interpolate(pointCollection, 1.0, {
      gridType: 'point' as const,
      property: 'value',
      weight: 2,
    });

    const breaks = generateBreaks(colorMode, levels);
    try {
      const contours = isolines(interpolated, breaks, { zProperty: 'value' });
      for (const feature of contours.features) {
        const val = feature.properties?.value;
        if (val != null) {
          feature.properties = {
            ...feature.properties,
            color: colorForValue(colorMode, val),
            label: String(Math.round(val * 100) / 100),
          };
        }
      }
      return contours;
    } catch {
      return { type: 'FeatureCollection', features: [] };
    }
  }, [gridCells, colorMode, levels]);

  // Add/update sources and layers
  useEffect(() => {
    if (!map || !map.isStyleLoaded()) return;

    const addSourcesAndLayers = () => {
      // ── Heatmap (replaces broken blurred circles) ──
      if (!map.getSource(HEATMAP_SOURCE)) {
        map.addSource(HEATMAP_SOURCE, {
          type: 'geojson',
          data: heatmapGeoJSON,
        });
      } else {
        (map.getSource(HEATMAP_SOURCE) as maplibregl.GeoJSONSource).setData(heatmapGeoJSON);
      }

      if (!map.getLayer(HEATMAP_LAYER)) {
        map.addLayer({
          id: HEATMAP_LAYER,
          type: 'heatmap',
          source: HEATMAP_SOURCE,
          paint: {
            'heatmap-weight': ['get', 'weight'],
            'heatmap-radius': [
              'interpolate', ['linear'], ['zoom'],
              10, 20,
              12, 30,
              14, 40,
            ],
            'heatmap-intensity': [
              'interpolate', ['linear'], ['zoom'],
              10, 0.6,
              14, 1.0,
            ],
            'heatmap-color': getHeatmapColorExpr(colorMode),
            // Fade out at high zoom to reveal grid cells
            'heatmap-opacity': [
              'interpolate', ['linear'], ['zoom'],
              12, 0.7,
              14, 0.4,
              16, 0.1,
            ],
          },
        });
      }

      // ── Contour isolines ──
      if (!map.getSource(CONTOUR_LINE_SOURCE)) {
        map.addSource(CONTOUR_LINE_SOURCE, {
          type: 'geojson',
          data: contourGeoJSON,
        });
      } else {
        (map.getSource(CONTOUR_LINE_SOURCE) as maplibregl.GeoJSONSource).setData(contourGeoJSON);
      }

      if (!map.getLayer(CONTOUR_LINE_LAYER)) {
        map.addLayer({
          id: CONTOUR_LINE_LAYER,
          type: 'line',
          source: CONTOUR_LINE_SOURCE,
          paint: {
            'line-color': ['get', 'color'],
            'line-width': 1.5,
            'line-opacity': 0.6,
          },
          layout: {
            'line-cap': 'round',
            'line-join': 'round',
          },
        });
      }

      if (!map.getLayer(CONTOUR_LABEL_LAYER)) {
        map.addLayer({
          id: CONTOUR_LABEL_LAYER,
          type: 'symbol',
          source: CONTOUR_LINE_SOURCE,
          layout: {
            'symbol-placement': 'line',
            'text-field': ['get', 'label'],
            'text-size': 10,
            'text-font': ['Open Sans Bold', 'Arial Unicode MS Bold'],
            'text-allow-overlap': false,
            'text-offset': [0, -0.5],
          },
          paint: {
            'text-color': ['get', 'color'],
            'text-halo-color': '#ffffff',
            'text-halo-width': 1.5,
          },
        });
      }

      addedRef.current = true;
    };

    if (map.isStyleLoaded()) {
      addSourcesAndLayers();
    } else {
      map.on('load', addSourcesAndLayers);
    }

    return () => {
      if (!addedRef.current) return;
      for (const layerId of [CONTOUR_LABEL_LAYER, CONTOUR_LINE_LAYER, HEATMAP_LAYER]) {
        if (map.getLayer(layerId)) map.removeLayer(layerId);
      }
      for (const sourceId of [CONTOUR_LINE_SOURCE, HEATMAP_SOURCE]) {
        if (map.getSource(sourceId)) map.removeSource(sourceId);
      }
      addedRef.current = false;
    };
  }, [map, heatmapGeoJSON, contourGeoJSON, colorMode]);

  // Update heatmap color ramp when colorMode changes
  useEffect(() => {
    if (!map || !addedRef.current) return;
    if (map.getLayer(HEATMAP_LAYER)) {
      map.setPaintProperty(HEATMAP_LAYER, 'heatmap-color', getHeatmapColorExpr(colorMode));
    }
  }, [map, colorMode]);

  // Toggle visibility
  useEffect(() => {
    if (!map || !addedRef.current) return;

    const visibility = visible ? 'visible' : 'none';
    for (const layerId of [HEATMAP_LAYER, CONTOUR_LINE_LAYER, CONTOUR_LABEL_LAYER]) {
      if (map.getLayer(layerId)) {
        map.setLayoutProperty(layerId, 'visibility', visibility);
      }
    }
  }, [map, visible]);

  return null;
}
