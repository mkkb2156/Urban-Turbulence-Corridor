import { useEffect, useRef, useCallback } from 'react';
import type maplibregl from 'maplibre-gl';
import type { GridCell } from '../../api/types';

interface WindParticleLayerProps {
  map: maplibregl.Map | null;
  gridCells?: GridCell[];
  visible: boolean;
}

// Particle system configuration
const MAX_PARTICLES = 2000;
const PARTICLE_LIFETIME = 80; // frames
const SPEED_FACTOR = 0.00004; // lon/lat units per m/s per frame
const FADE_TAIL = 0.92; // trail opacity decay

interface Particle {
  x: number; // lon
  y: number; // lat
  age: number;
  maxAge: number;
  speed: number;
}

function windSpeedColor(speed: number): string {
  if (speed <= 3) return 'rgba(59, 130, 246, 0.8)';   // blue
  if (speed <= 5) return 'rgba(34, 197, 94, 0.8)';    // green
  if (speed <= 8) return 'rgba(234, 179, 8, 0.8)';    // yellow
  if (speed <= 12) return 'rgba(239, 68, 68, 0.8)';   // red
  return 'rgba(127, 29, 29, 0.9)';                     // dark red
}

/**
 * Build a simple wind field lookup from grid cells.
 * Returns a function that interpolates wind at any (lon, lat).
 */
function buildWindField(cells: GridCell[]) {
  if (!cells.length) return null;

  // Find bounds
  let minLon = Infinity, maxLon = -Infinity, minLat = Infinity, maxLat = -Infinity;
  for (const c of cells) {
    if (c.lon < minLon) minLon = c.lon;
    if (c.lon > maxLon) maxLon = c.lon;
    if (c.lat < minLat) minLat = c.lat;
    if (c.lat > maxLat) maxLat = c.lat;
  }

  // Parse wind_direction from cells (string -> number)
  const parsedCells = cells.map((c) => {
    const dirDeg = parseFloat(c.wind_direction) || 45;
    const rad = (dirDeg * Math.PI) / 180;
    // Wind "from" direction → movement vector is opposite
    const u = -c.wind_speed * Math.sin(rad);
    const v = -c.wind_speed * Math.cos(rad);
    return { lon: c.lon, lat: c.lat, u, v, speed: c.wind_speed };
  });

  return {
    bounds: { minLon, maxLon, minLat, maxLat },
    getWind(lon: number, lat: number): { u: number; v: number; speed: number } | null {
      // Simple inverse-distance weighted interpolation from nearest 4 cells
      const pad = 0.01;
      if (lon < minLon - pad || lon > maxLon + pad || lat < minLat - pad || lat > maxLat + pad) {
        return null;
      }

      let totalW = 0;
      let su = 0, sv = 0, ss = 0;
      const maxDist = 0.015; // ~1.5 km in degrees

      for (const c of parsedCells) {
        const dx = lon - c.lon;
        const dy = lat - c.lat;
        const d2 = dx * dx + dy * dy;
        if (d2 < 1e-10) {
          return { u: c.u, v: c.v, speed: c.speed };
        }
        if (d2 > maxDist * maxDist) continue;
        const w = 1 / d2;
        totalW += w;
        su += w * c.u;
        sv += w * c.v;
        ss += w * c.speed;
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
      maxAge: PARTICLE_LIFETIME + Math.floor(Math.random() * 30),
      speed: 0,
    };
  }, []);

  useEffect(() => {
    if (!map || !visible) {
      // Clean up
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

    // Animation loop
    const animate = () => {
      const wf = windFieldRef.current;
      if (!wf || !canvasRef.current) {
        animRef.current = requestAnimationFrame(animate);
        return;
      }

      // Fade previous frame
      ctx.globalCompositeOperation = 'destination-in';
      ctx.fillStyle = `rgba(0, 0, 0, ${FADE_TAIL})`;
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

        // Opacity based on age (fade in/out)
        const ageRatio = p.age / p.maxAge;
        const opacity = ageRatio < 0.1 ? ageRatio * 10 : ageRatio > 0.8 ? (1 - ageRatio) * 5 : 1;

        ctx.beginPath();
        ctx.moveTo(from.x, from.y);
        ctx.lineTo(to.x, to.y);
        ctx.strokeStyle = windSpeedColor(p.speed).replace('0.8', String(0.8 * opacity));
        ctx.lineWidth = Math.max(0.8, Math.min(2, p.speed / 6));
        ctx.stroke();
      }

      animRef.current = requestAnimationFrame(animate);
    };

    animRef.current = requestAnimationFrame(animate);

    // Redraw on map move
    const onMove = () => {
      // Canvas stays in sync via CSS, just keep animating
    };
    map.on('move', onMove);

    return () => {
      if (animRef.current) {
        cancelAnimationFrame(animRef.current);
        animRef.current = 0;
      }
      map.off('resize', onResize);
      map.off('move', onMove);
      if (canvasRef.current) {
        canvasRef.current.remove();
        canvasRef.current = null;
      }
    };
  }, [map, visible, randomParticle]);

  return null; // Renders via canvas overlay, no React DOM
}
