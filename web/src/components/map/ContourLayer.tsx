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
  /** Show filled isobands instead of just lines */
  showFill?: boolean;
}

const CONTOUR_LINE_SOURCE = 'contour-lines';
const CONTOUR_LINE_LAYER = 'contour-lines-layer';
const CONTOUR_LABEL_LAYER = 'contour-labels-layer';
const INTERPOLATED_SOURCE = 'interpolated-field';
const INTERPOLATED_LAYER = 'interpolated-field-layer';

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

/**
 * Generate contour break values for a given color mode.
 */
function generateBreaks(mode: MapColorMode, levels: number): number[] {
  const range = COLOR_MODE_RANGES[mode];
  const breaks: number[] = [];
  const step = (range.max - range.min) / (levels + 1);
  for (let i = 1; i <= levels; i++) {
    breaks.push(range.min + step * i);
  }
  return breaks;
}

export default function ContourLayer({
  map,
  gridCells,
  visible,
  colorMode,
  levels = 8,
  showFill = true,
}: ContourLayerProps) {
  const addedRef = useRef(false);

  // Compute interpolated grid and contour lines
  const { contourGeoJSON, interpolatedGeoJSON } = useMemo(() => {
    if (!gridCells?.length) {
      return {
        contourGeoJSON: { type: 'FeatureCollection' as const, features: [] },
        interpolatedGeoJSON: { type: 'FeatureCollection' as const, features: [] },
      };
    }

    // Build point features with values
    const points = gridCells
      .map((cell) => {
        const value = getCellValue(cell, colorMode);
        if (value == null) return null;
        return point([cell.lon, cell.lat], { value });
      })
      .filter((p): p is NonNullable<typeof p> => p !== null);

    if (points.length < 3) {
      return {
        contourGeoJSON: { type: 'FeatureCollection' as const, features: [] },
        interpolatedGeoJSON: { type: 'FeatureCollection' as const, features: [] },
      };
    }

    const pointCollection = featureCollection(points);

    // IDW interpolation to create a denser point grid
    const interpolated = interpolate(pointCollection, 0.3, {
      gridType: 'point' as const,
      property: 'value',
      weight: 2,
    });

    // Color each interpolated point
    for (const feature of interpolated.features) {
      const val = feature.properties?.value;
      if (val != null) {
        feature.properties = {
          ...feature.properties,
          color: colorForValue(colorMode, val),
        };
      }
    }

    // Generate contour lines (isolines)
    const breaks = generateBreaks(colorMode, levels);
    let contours: GeoJSON.FeatureCollection;
    try {
      contours = isolines(interpolated, breaks, { zProperty: 'value' });
      // Add color to each contour line
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
    } catch {
      contours = { type: 'FeatureCollection', features: [] };
    }

    return {
      contourGeoJSON: contours,
      interpolatedGeoJSON: interpolated,
    };
  }, [gridCells, colorMode, levels]);

  // Add/update sources and layers
  useEffect(() => {
    if (!map || !map.isStyleLoaded()) return;

    const addSourcesAndLayers = () => {
      // Interpolated field (filled circles for smooth heatmap effect)
      if (!map.getSource(INTERPOLATED_SOURCE)) {
        map.addSource(INTERPOLATED_SOURCE, {
          type: 'geojson',
          data: interpolatedGeoJSON,
        });
      } else {
        (map.getSource(INTERPOLATED_SOURCE) as maplibregl.GeoJSONSource).setData(
          interpolatedGeoJSON as GeoJSON.FeatureCollection,
        );
      }

      if (!map.getLayer(INTERPOLATED_LAYER)) {
        map.addLayer({
          id: INTERPOLATED_LAYER,
          type: 'circle',
          source: INTERPOLATED_SOURCE,
          paint: {
            'circle-radius': [
              'interpolate', ['linear'], ['zoom'],
              11, 8,
              13, 14,
              15, 22,
            ],
            'circle-color': ['get', 'color'],
            'circle-opacity': showFill ? 0.4 : 0,
            'circle-blur': 0.8,
          },
        });
      }

      // Contour lines
      if (!map.getSource(CONTOUR_LINE_SOURCE)) {
        map.addSource(CONTOUR_LINE_SOURCE, {
          type: 'geojson',
          data: contourGeoJSON,
        });
      } else {
        (map.getSource(CONTOUR_LINE_SOURCE) as maplibregl.GeoJSONSource).setData(
          contourGeoJSON as GeoJSON.FeatureCollection,
        );
      }

      if (!map.getLayer(CONTOUR_LINE_LAYER)) {
        map.addLayer({
          id: CONTOUR_LINE_LAYER,
          type: 'line',
          source: CONTOUR_LINE_SOURCE,
          paint: {
            'line-color': ['get', 'color'],
            'line-width': 1.5,
            'line-opacity': 0.7,
          },
          layout: {
            'line-cap': 'round',
            'line-join': 'round',
          },
        });
      }

      // Contour labels
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
      // Cleanup layers and sources on unmount
      for (const layerId of [CONTOUR_LABEL_LAYER, CONTOUR_LINE_LAYER, INTERPOLATED_LAYER]) {
        if (map.getLayer(layerId)) {
          map.removeLayer(layerId);
        }
      }
      for (const sourceId of [CONTOUR_LINE_SOURCE, INTERPOLATED_SOURCE]) {
        if (map.getSource(sourceId)) {
          map.removeSource(sourceId);
        }
      }
      addedRef.current = false;
    };
  }, [map, contourGeoJSON, interpolatedGeoJSON, showFill]);

  // Toggle visibility
  useEffect(() => {
    if (!map || !addedRef.current) return;

    const visibility = visible ? 'visible' : 'none';
    for (const layerId of [CONTOUR_LINE_LAYER, CONTOUR_LABEL_LAYER, INTERPOLATED_LAYER]) {
      if (map.getLayer(layerId)) {
        map.setLayoutProperty(layerId, 'visibility', visibility);
      }
    }
  }, [map, visible]);

  return null;
}
