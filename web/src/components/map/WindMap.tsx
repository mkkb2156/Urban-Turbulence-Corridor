import { useRef, useEffect, useCallback, useState } from 'react';
import maplibregl from 'maplibre-gl';
import type { GridCell, Corridor, MapLayers, HeightOption } from '../../api/types';
import { RISK_COLORS, CORRIDOR_COLORS } from '../../utils/colors';
import { DEFAULT_CENTER, DEFAULT_ZOOM, gridCellPolygon } from '../../utils/geo';
import MapControls from './MapControls';
import RiskLegend from './RiskLegend';
import GridPopup from './GridPopup';

interface WindMapProps {
  gridCells?: GridCell[];
  corridors?: Corridor[];
  height: HeightOption;
  onHeightChange: (h: HeightOption) => void;
  layers: MapLayers;
  onLayersChange: (layers: MapLayers) => void;
  isLoading?: boolean;
}

export default function WindMap({
  gridCells,
  corridors,
  height,
  onHeightChange,
  layers,
  onLayersChange,
  isLoading,
}: WindMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [selectedCell, setSelectedCell] = useState<GridCell | null>(null);
  const [popupPosition, setPopupPosition] = useState<{ x: number; y: number } | null>(null);

  // Initialize map
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: {
        version: 8,
        sources: {
          'osm-tiles': {
            type: 'raster',
            tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
            tileSize: 256,
            attribution: '&copy; OpenStreetMap contributors',
          },
        },
        layers: [
          {
            id: 'osm-tiles',
            type: 'raster',
            source: 'osm-tiles',
            minzoom: 0,
            maxzoom: 19,
          },
        ],
      },
      center: DEFAULT_CENTER,
      zoom: DEFAULT_ZOOM,
      maxBounds: [
        [118.5, 20.5],
        [123.5, 26.5],
      ],
    });

    map.addControl(new maplibregl.NavigationControl(), 'top-right');
    map.addControl(
      new maplibregl.ScaleControl({ maxWidth: 200 }),
      'bottom-right',
    );

    map.on('load', () => {
      // Add empty sources that will be updated with data
      map.addSource('grid-cells', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      });

      map.addSource('corridors', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      });

      // Grid cell fill layer
      map.addLayer({
        id: 'grid-cells-fill',
        type: 'fill',
        source: 'grid-cells',
        paint: {
          'fill-color': ['get', 'color'],
          'fill-opacity': 0.5,
        },
      });

      // Grid cell outline layer
      map.addLayer({
        id: 'grid-cells-outline',
        type: 'line',
        source: 'grid-cells',
        paint: {
          'line-color': ['get', 'color'],
          'line-width': 1,
          'line-opacity': 0.7,
        },
      });

      // Corridor lines - primary
      map.addLayer({
        id: 'corridors-primary',
        type: 'line',
        source: 'corridors',
        filter: ['==', ['get', 'type'], 'primary'],
        paint: {
          'line-color': CORRIDOR_COLORS.primary,
          'line-width': 4,
          'line-opacity': 0.8,
        },
        layout: {
          'line-cap': 'round',
          'line-join': 'round',
        },
      });

      // Corridor lines - secondary
      map.addLayer({
        id: 'corridors-secondary',
        type: 'line',
        source: 'corridors',
        filter: ['==', ['get', 'type'], 'secondary'],
        paint: {
          'line-color': CORRIDOR_COLORS.secondary,
          'line-width': 2,
          'line-opacity': 0.6,
        },
        layout: {
          'line-cap': 'round',
          'line-join': 'round',
        },
      });
    });

    // Click handler for grid cells
    map.on('click', 'grid-cells-fill', (e) => {
      if (!e.features?.length) return;
      const feature = e.features[0];
      const props = feature.properties;
      if (props) {
        setSelectedCell({
          grid_id: props.grid_id as string,
          lon: props.lon as number,
          lat: props.lat as number,
          risk_level: props.risk_level as GridCell['risk_level'],
          risk_score: props.risk_score as number,
          wind_speed: props.wind_speed as number,
          wind_direction: props.wind_direction as string,
          is_corridor: props.is_corridor as boolean,
        });
        setPopupPosition({ x: e.point.x, y: e.point.y });
      }
    });

    // Cursor change on hover
    map.on('mouseenter', 'grid-cells-fill', () => {
      map.getCanvas().style.cursor = 'pointer';
    });
    map.on('mouseleave', 'grid-cells-fill', () => {
      map.getCanvas().style.cursor = '';
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Update grid cells data
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    const source = map.getSource('grid-cells') as maplibregl.GeoJSONSource | undefined;
    if (!source) return;

    if (!gridCells || !layers.risk) {
      source.setData({ type: 'FeatureCollection', features: [] });
      return;
    }

    const features: GeoJSON.Feature[] = gridCells.map((cell) => ({
      type: 'Feature' as const,
      geometry: {
        type: 'Polygon' as const,
        coordinates: [gridCellPolygon(cell.lon, cell.lat)],
      },
      properties: {
        ...cell,
        color: RISK_COLORS[cell.risk_level],
      },
    }));

    source.setData({
      type: 'FeatureCollection',
      features,
    });
  }, [gridCells, layers.risk]);

  // Update corridors data
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    const source = map.getSource('corridors') as maplibregl.GeoJSONSource | undefined;
    if (!source) return;

    if (!corridors || !layers.corridors) {
      source.setData({ type: 'FeatureCollection', features: [] });
      return;
    }

    const features: GeoJSON.Feature[] = corridors.map((corridor) => ({
      type: 'Feature' as const,
      geometry: corridor.geometry,
      properties: {
        corridor_id: corridor.corridor_id,
        name: corridor.name,
        type: corridor.type,
        mean_wind_speed: corridor.mean_wind_speed,
      },
    }));

    source.setData({
      type: 'FeatureCollection',
      features,
    });
  }, [corridors, layers.corridors]);

  // Toggle layer visibility
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    const setLayerVisibility = (layerId: string, visible: boolean) => {
      if (map.getLayer(layerId)) {
        map.setLayoutProperty(layerId, 'visibility', visible ? 'visible' : 'none');
      }
    };

    setLayerVisibility('grid-cells-fill', layers.risk);
    setLayerVisibility('grid-cells-outline', layers.risk);
    setLayerVisibility('corridors-primary', layers.corridors);
    setLayerVisibility('corridors-secondary', layers.corridors);
  }, [layers]);

  const handleClosePopup = useCallback(() => {
    setSelectedCell(null);
    setPopupPosition(null);
  }, []);

  return (
    <div className="relative h-full w-full">
      {/* Map container */}
      <div ref={containerRef} className="h-full w-full rounded-lg" />

      {/* Loading overlay */}
      {isLoading && (
        <div className="absolute inset-0 z-10 flex items-center justify-center rounded-lg bg-white/50 dark:bg-gray-900/50">
          <div className="flex items-center gap-2 rounded-md bg-white px-4 py-2 shadow dark:bg-gray-800">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
            <span className="text-sm text-gray-600 dark:text-gray-300">
              Loading map data...
            </span>
          </div>
        </div>
      )}

      {/* Map controls overlay */}
      <div className="absolute left-3 top-3 z-10">
        <MapControls
          height={height}
          onHeightChange={onHeightChange}
          layers={layers}
          onLayersChange={onLayersChange}
        />
      </div>

      {/* Risk legend */}
      <div className="absolute bottom-8 left-3 z-10">
        <RiskLegend />
      </div>

      {/* Grid popup */}
      {selectedCell && popupPosition && (
        <div
          className="absolute z-20"
          style={{
            left: popupPosition.x + 10,
            top: popupPosition.y - 10,
          }}
        >
          <GridPopup cell={selectedCell} onClose={handleClosePopup} />
        </div>
      )}
    </div>
  );
}
