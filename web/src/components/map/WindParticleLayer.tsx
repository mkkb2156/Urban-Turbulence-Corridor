import { useEffect, useRef, useCallback } from 'react';
import type maplibregl from 'maplibre-gl';
import chroma from 'chroma-js';
import type { GridCell } from '../../api/types';
import { directionToDegrees } from '../../utils/geo';

interface WindParticleLayerProps {
  map: maplibregl.Map | null;
  gridCells?: GridCell[];
  visible: boolean;
}

// ─── Particle system configuration ─────────────────────────────
const MAX_PARTICLES = 3000;
const PARTICLE_LIFETIME = 100; // frames
const SPEED_FACTOR = 0.00004; // lon/lat units per m/s per frame
const FADE_TAIL = 0.93; // trail opacity decay

// ─── Wind speed color scale (chroma.js Lab space) ──────────────
const particleColorScale = chroma
  .scale(['#60a5fa', '#34d399', '#fbbf24', '#f87171', '#991b1b'])
  .domain([0, 3, 6, 10, 15])
  .mode('lab');

function windSpeedColorRGBA(speed: number, opacity: number): string {
  const color = particleColorScale(Math.min(speed, 15));
  return color.alpha(opacity).css();
}

interface Particle {
  x: number; // lon
  y: number; // lat
  age: number;
  maxAge: number;
  speed: number;
}

/**
 * Build a spatial wind field index from grid cells.
 * Uses a hash grid for O(1) neighbor lookups instead of O(n) scan.
 */
function buildWindField(cells: GridCell[]) {
  if (!cells.length) return null;

  let minLon = Infinity, maxLon = -Infinity, minLat = Infinity, maxLat = -Infinity;
  for (const c of cells) {
    if (c.lon < minLon) minLon = c.lon;
    if (c.lon > maxLon) maxLon = c.lon;
    if (c.lat < minLat) minLat = c.lat;
    if (c.lat > maxLat) maxLat = c.lat;
  }

  // Parse wind vectors
  const parsedCells = cells.map((c) => {
    const dirDeg = directionToDegrees(c.wind_direction) ?? 45;
    const rad = (dirDeg * Math.PI) / 180;
    const u = -c.wind_speed * Math.sin(rad);
    const v = -c.wind_speed * Math.cos(rad);
    return { lon: c.lon, lat: c.lat, u, v, speed: c.wind_speed };
  });

  // Build spatial hash grid for fast lookups
  const CELL_SIZE = 0.006; // ~600m buckets
  const buckets = new Map<string, typeof parsedCells>();

  for (const c of parsedCells) {
    const bx = Math.floor(c.lon / CELL_SIZE);
    const by = Math.floor(c.lat / CELL_SIZE);
    const key = `${bx},${by}`;
    if (!buckets.has(key)) buckets.set(key, []);
    buckets.get(key)!.push(c);
  }

  return {
    bounds: { minLon, maxLon, minLat, maxLat },
    getWind(lon: number, lat: number): { u: number; v: number; speed: number } | null {
      const pad = 0.01;
      if (lon < minLon - pad || lon > maxLon + pad || lat < minLat - pad || lat > maxLat + pad) {
        return null;
      }

      // Search in neighboring buckets
      const bx = Math.floor(lon / CELL_SIZE);
      const by = Math.floor(lat / CELL_SIZE);
      const maxDist2 = 0.015 * 0.015;

      let totalW = 0;
      let su = 0, sv = 0, ss = 0;

      for (let dx = -1; dx <= 1; dx++) {
        for (let dy = -1; dy <= 1; dy++) {
          const bucket = buckets.get(`${bx + dx},${by + dy}`);
          if (!bucket) continue;

          for (const c of bucket) {
            const ddx = lon - c.lon;
            const ddy = lat - c.lat;
            const d2 = ddx * ddx + ddy * ddy;
            if (d2 < 1e-10) {
              return { u: c.u, v: c.v, speed: c.speed };
            }
            if (d2 > maxDist2) continue;
            const w = 1 / d2;
            totalW += w;
            su += w * c.u;
            sv += w * c.v;
            ss += w * c.speed;
          }
        }
      }

      if (totalW === 0) return null;
      return { u: su / totalW, v: sv / totalW, speed: ss / totalW };
    },
  };
}

export default function WindParticleLayer({ map, gridCells, visible }: WindParticleLayerProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animRef = useRef<number>(0);
  const particlesRef = useRef<Particle[]>([]);
  const windFieldRef = useRef<ReturnType<typeof buildWindField>>(null);

  // Rebuild wind field when grid cells change
  useEffect(() => {
    windFieldRef.current = gridCells?.length ? buildWindField(gridCells) : null;
  }, [gridCells]);

  const randomParticle = useCallback((): Particle => {
    const wf = windFieldRef.current;
    if (!wf) {
      return { x: 121.5, y: 25.0, age: 999, maxAge: 1, speed: 0 };
    }
    const { minLon, maxLon, minLat, maxLat } = wf.bounds;
    return {
      x: minLon + Math.random() * (maxLon - minLon),
      y: minLat + Math.random() * (maxLat - minLat),
      age: Math.floor(Math.random() * PARTICLE_LIFETIME),
      maxAge: PARTICLE_LIFETIME + Math.floor(Math.random() * 40),
      speed: 0,
    };
  }, []);

  useEffect(() => {
    if (!map || !visible) {
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

    // Create overlay canvas
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

    // Initialize particles
    const particles: Particle[] = [];
    for (let i = 0; i < MAX_PARTICLES; i++) {
      particles.push(randomParticle());
    }
    particlesRef.current = particles;

    // Resize handler
    const onResize = () => {
      const mc = map.getCanvas();
      canvas.width = mc.width;
      canvas.height = mc.height;
      canvas.style.width = mc.style.width;
      canvas.style.height = mc.style.height;
    };
    map.on('resize', onResize);

    // Clear trails on pan/zoom for better visual sync
    let isMoving = false;
    const onMoveStart = () => { isMoving = true; };
    const onMoveEnd = () => { isMoving = false; };
    map.on('movestart', onMoveStart);
    map.on('moveend', onMoveEnd);

    // Animation loop
    const animate = () => {
      const wf = windFieldRef.current;
      if (!wf || !canvasRef.current) {
        animRef.current = requestAnimationFrame(animate);
        return;
      }

      // Fade previous frame (faster fade during panning for cleaner look)
      ctx.globalCompositeOperation = 'destination-in';
      const fadeFactor = isMoving ? 0.85 : FADE_TAIL;
      ctx.fillStyle = `rgba(0, 0, 0, ${fadeFactor})`;
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.globalCompositeOperation = 'source-over';

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        p.age++;

        if (p.age >= p.maxAge) {
          particles[i] = randomParticle();
          particles[i].age = 0;
          continue;
        }

        const wind = wf.getWind(p.x, p.y);
        if (!wind) {
          particles[i] = randomParticle();
          particles[i].age = 0;
          continue;
        }

        const oldX = p.x;
        const oldY = p.y;
        p.x += wind.u * SPEED_FACTOR;
        p.y += wind.v * SPEED_FACTOR;
        p.speed = wind.speed;

        // Project to screen
        const from = map.project([oldX, oldY]);
        const to = map.project([p.x, p.y]);

        // Opacity: fade in during first 10% of life, fade out during last 20%
        const ageRatio = p.age / p.maxAge;
        const opacity = ageRatio < 0.1
          ? ageRatio * 10
          : ageRatio > 0.8
            ? (1 - ageRatio) * 5
            : 1;

        ctx.beginPath();
        ctx.moveTo(from.x, from.y);
        ctx.lineTo(to.x, to.y);
        ctx.strokeStyle = windSpeedColorRGBA(p.speed, 0.8 * opacity);
        // Line width scales with speed: min 0.8px (calm) → max 2.5px (strong)
        ctx.lineWidth = Math.max(0.8, Math.min(2.5, p.speed / 5));
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
      map.off('movestart', onMoveStart);
      map.off('moveend', onMoveEnd);
      if (canvasRef.current) {
        canvasRef.current.remove();
        canvasRef.current = null;
      }
    };
  }, [map, visible, randomParticle]);

  return null;
}
