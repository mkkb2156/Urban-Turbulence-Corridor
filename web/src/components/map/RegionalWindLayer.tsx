import { useEffect, useRef, useState, useCallback } from 'react';
import type maplibregl from 'maplibre-gl';
import chroma from 'chroma-js';
import apiClient from '../../api/client';
import type { RegionalWindResponse, RegionalWindPoint } from '../../api/types';

interface RegionalWindLayerProps {
  map: maplibregl.Map | null;
  visible: boolean;
  height?: number;
}

// ─── Configuration ─────────────────────────────────────────────
const ZOOM_THRESHOLD = 11; // Below this zoom, show regional; above, let grid cells handle it
const MAX_PARTICLES = 4000;
const PARTICLE_LIFETIME = 120;
const SPEED_FACTOR = 0.00012; // Larger scale for regional view
const FADE_TAIL = 0.94;

const regionColorScale = chroma
  .scale(['#93c5fd', '#6ee7b7', '#fbbf24', '#f87171', '#7f1d1d'])
  .domain([0, 4, 8, 12, 18])
  .mode('lab');

interface Particle {
  x: number;
  y: number;
  age: number;
  maxAge: number;
  speed: number;
}

const REGIONAL_ARROWS_SOURCE = 'regional-wind-arrows';
const REGIONAL_ARROWS_LAYER = 'regional-wind-arrows-layer';
const REGIONAL_RISK_SOURCE = 'regional-risk-dots';
const REGIONAL_RISK_LAYER = 'regional-risk-dots-layer';

function buildRegionalWindField(points: RegionalWindPoint[]) {
  if (!points.length) return null;

  let minLon = Infinity, maxLon = -Infinity, minLat = Infinity, maxLat = -Infinity;
  for (const p of points) {
    if (p.lon < minLon) minLon = p.lon;
    if (p.lon > maxLon) maxLon = p.lon;
    if (p.lat < minLat) minLat = p.lat;
    if (p.lat > maxLat) maxLat = p.lat;
  }

  return {
    bounds: { minLon, maxLon, minLat, maxLat },
    getWind(lon: number, lat: number): { u: number; v: number; speed: number } | null {
      const pad = 0.15;
      if (lon < minLon - pad || lon > maxLon + pad || lat < minLat - pad || lat > maxLat + pad) {
        return null;
      }

      // Bilinear-ish interpolation from nearest points
      let totalW = 0;
      let su = 0, sv = 0, ss = 0;
      const maxDist = 0.2; // ~20km
      const maxDist2 = maxDist * maxDist;

      for (const p of points) {
        const dx = lon - p.lon;
        const dy = lat - p.lat;
        const d2 = dx * dx + dy * dy;
        if (d2 < 1e-8) return { u: p.u, v: p.v, speed: p.wind_speed };
        if (d2 > maxDist2) continue;
        const w = 1 / d2;
        totalW += w;
        su += w * p.u;
        sv += w * p.v;
        ss += w * p.wind_speed;
      }

      if (totalW === 0) return null;
      return { u: su / totalW, v: sv / totalW, speed: ss / totalW };
    },
  };
}

export default function RegionalWindLayer({ map, visible, height = 10 }: RegionalWindLayerProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animRef = useRef<number>(0);
  const windFieldRef = useRef<ReturnType<typeof buildRegionalWindField>>(null);
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
      windFieldRef.current = buildRegionalWindField(data.points);
    } catch (err) {
      console.warn('Regional wind fetch failed:', err);
    }
  }, [map, height]);

  // Fetch on mount and when map moves significantly
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

  // Add vector layers for wind arrows and risk dots
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
            'circle-opacity': 0.35,
            'circle-blur': 0.6,
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

  // Particle animation for regional wind
  useEffect(() => {
    if (!map || !visible || !isActive) {
      if (canvasRef.current) {
        canvasRef.current.remove();
        canvasRef.current = null;
      }
      if (animRef.current) {
        cancelAnimationFrame(animRef.current);
        animRef.current = 0;
      }
      return;
    }

    const container = map.getCanvasContainer();
    const mapCanvas = map.getCanvas();
    const canvas = document.createElement('canvas');
    canvas.width = mapCanvas.width;
    canvas.height = mapCanvas.height;
    canvas.style.position = 'absolute';
    canvas.style.top = '0';
    canvas.style.left = '0';
    canvas.style.width = mapCanvas.style.width;
    canvas.style.height = mapCanvas.style.height;
    canvas.style.pointerEvents = 'none';
    container.appendChild(canvas);
    canvasRef.current = canvas;

    const ctx = canvas.getContext('2d')!;

    const wf = windFieldRef.current;
    if (!wf) return;

    const { minLon, maxLon, minLat, maxLat } = wf.bounds;
    const particles: Particle[] = [];
    for (let i = 0; i < MAX_PARTICLES; i++) {
      particles.push({
        x: minLon + Math.random() * (maxLon - minLon),
        y: minLat + Math.random() * (maxLat - minLat),
        age: Math.floor(Math.random() * PARTICLE_LIFETIME),
        maxAge: PARTICLE_LIFETIME + Math.floor(Math.random() * 50),
        speed: 0,
      });
    }

    const onResize = () => {
      const mc = map.getCanvas();
      canvas.width = mc.width;
      canvas.height = mc.height;
      canvas.style.width = mc.style.width;
      canvas.style.height = mc.style.height;
    };
    map.on('resize', onResize);

    const animate = () => {
      const field = windFieldRef.current;
      if (!field || !canvasRef.current) {
        animRef.current = requestAnimationFrame(animate);
        return;
      }

      ctx.globalCompositeOperation = 'destination-in';
      ctx.fillStyle = `rgba(0, 0, 0, ${FADE_TAIL})`;
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.globalCompositeOperation = 'source-over';

      const bounds = field.bounds;

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        p.age++;

        if (p.age >= p.maxAge) {
          particles[i] = {
            x: bounds.minLon + Math.random() * (bounds.maxLon - bounds.minLon),
            y: bounds.minLat + Math.random() * (bounds.maxLat - bounds.minLat),
            age: 0,
            maxAge: PARTICLE_LIFETIME + Math.floor(Math.random() * 50),
            speed: 0,
          };
          continue;
        }

        const wind = field.getWind(p.x, p.y);
        if (!wind) {
          particles[i].age = particles[i].maxAge;
          continue;
        }

        const oldX = p.x;
        const oldY = p.y;
        p.x += wind.u * SPEED_FACTOR;
        p.y += wind.v * SPEED_FACTOR;
        p.speed = wind.speed;

        const from = map.project([oldX, oldY]);
        const to = map.project([p.x, p.y]);

        const ageRatio = p.age / p.maxAge;
        const opacity = ageRatio < 0.1 ? ageRatio * 10 : ageRatio > 0.8 ? (1 - ageRatio) * 5 : 1;

        const color = regionColorScale(Math.min(p.speed, 18));
        ctx.beginPath();
        ctx.moveTo(from.x, from.y);
        ctx.lineTo(to.x, to.y);
        ctx.strokeStyle = color.alpha(0.6 * opacity).css();
        ctx.lineWidth = Math.max(1, Math.min(3, p.speed / 4));
        ctx.stroke();
      }

      animRef.current = requestAnimationFrame(animate);
    };

    animRef.current = requestAnimationFrame(animate);

    return () => {
      if (animRef.current) {
        cancelAnimationFrame(animRef.current);
        animRef.current = 0;
      }
      map.off('resize', onResize);
      if (canvasRef.current) {
        canvasRef.current.remove();
        canvasRef.current = null;
      }
    };
  }, [map, visible, isActive]);

  return null;
}
