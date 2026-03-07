import { useEffect } from 'react';
import type maplibregl from 'maplibre-gl';
import type { GridCell } from '../../api/types';
import { RISK_COLORS } from '../../utils/colors';
import { directionToDegrees } from '../../utils/geo';

/**
 * Create an SVG arrow image for MapLibre.
 */
function createArrowImage(color: string): HTMLCanvasElement {
  const size = 32;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d')!;

  ctx.fillStyle = color;
  ctx.beginPath();
  // Arrow pointing up (north = 0°)
  ctx.moveTo(size / 2, 2);        // tip
  ctx.lineTo(size - 6, size - 4); // right
  ctx.lineTo(size / 2, size - 10); // notch
  ctx.lineTo(6, size - 4);        // left
  ctx.closePath();
  ctx.fill();

  return canvas;
}

interface WindArrowLayerProps {
  map: maplibregl.Map | null;
  gridCells?: GridCell[];
  visible: boolean;
}

const SOURCE_ID = 'wind-arrows-source';
const LAYER_ID = 'wind-arrows-layer';

export default function WindArrowLayer({ map, gridCells, visible }: WindArrowLayerProps) {
  // Add arrow images
  useEffect(() => {
    if (!map || !map.isStyleLoaded()) return;

    const riskLevels = ['green', 'yellow', 'red', 'black'] as const;
    for (const level of riskLevels) {
      const imgId = `arrow-${level}`;
      if (!map.hasImage(imgId)) {
        const canvas = createArrowImage(RISK_COLORS[level]);
        map.addImage(imgId, { width: 32, height: 32, data: new Uint8Array(canvas.getContext('2d')!.getImageData(0, 0, 32, 32).data) });
      }
    }
  }, [map]);

  // Add/update source + layer
  useEffect(() => {
    if (!map || !map.isStyleLoaded()) return;

    // Create source if needed
    if (!map.getSource(SOURCE_ID)) {
      map.addSource(SOURCE_ID, {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      });
    }

    // Create layer if needed
    if (!map.getLayer(LAYER_ID)) {
      map.addLayer({
        id: LAYER_ID,
        type: 'symbol',
        source: SOURCE_ID,
        layout: {
          'icon-image': ['concat', 'arrow-', ['get', 'risk_level']],
          'icon-size': [
            'interpolate', ['linear'], ['get', 'wind_speed'],
            0, 0.3,
            5, 0.5,
            8, 0.8,
            12, 1.1,
            15, 1.4,
          ],
          'icon-rotate': ['get', 'wind_direction_deg'],
          'icon-rotation-alignment': 'map',
          'icon-allow-overlap': true,
          'icon-ignore-placement': true,
        },
        paint: {
          'icon-opacity': 0.85,
        },
      });
    }

    // Update visibility
    map.setLayoutProperty(LAYER_ID, 'visibility', visible ? 'visible' : 'none');

    // Update data
    if (!gridCells || !visible) {
      const src = map.getSource(SOURCE_ID) as maplibregl.GeoJSONSource | undefined;
      if (src) src.setData({ type: 'FeatureCollection', features: [] });
      return;
    }

    const features: GeoJSON.Feature[] = gridCells.map((cell) => {
      // Convert direction string to degrees
      const dirDeg = directionToDegrees(cell.wind_direction) ?? 45;
      return {
        type: 'Feature' as const,
        geometry: {
          type: 'Point' as const,
          coordinates: [cell.lon, cell.lat],
        },
        properties: {
          wind_speed: cell.wind_speed,
          wind_direction_deg: dirDeg,
          risk_level: cell.risk_level,
          grid_id: cell.grid_id,
        },
      };
    });

    const src = map.getSource(SOURCE_ID) as maplibregl.GeoJSONSource | undefined;
    if (src) {
      src.setData({ type: 'FeatureCollection', features });
    }
  }, [map, gridCells, visible]);

  return null; // Render-only logic, no DOM
}
