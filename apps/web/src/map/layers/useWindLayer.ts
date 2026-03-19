/**
 * useWindLayer — React hook that manages the WindLayer lifecycle
 *
 * Fetches the wind PNG texture via useWindTexture(), creates a WindLayer
 * custom layer instance, adds/removes it from the MapLibre map, and
 * updates the wind texture whenever new data arrives.
 */

import { useEffect, useRef, useCallback } from "react";
import type { MapRef } from "@vis.gl/react-maplibre";
import maplibregl from "maplibre-gl";
import { useWindTexture } from "@/api/hooks/useWindTexture";
import { WindLayer, type WindLayerOptions } from "./WindLayer";

interface UseWindLayerParams {
  /** React ref to the MapLibre map instance */
  mapRef: React.RefObject<MapRef | null>;
  /** Whether the wind field layer should be visible */
  enabled?: boolean;
  /** Override default layer options */
  options?: WindLayerOptions;
  /** Wind texture query params (bbox, datetime, altitude, resolution) */
  textureParams?: {
    bbox?: string;
    datetime?: string;
    altitude?: number;
    resolution?: number;
  };
}

interface UseWindLayerResult {
  /** The underlying WindLayer instance (null until map is ready) */
  layer: WindLayer | null;
  /** Whether wind texture data is currently loading */
  isLoading: boolean;
  /** Error from wind texture fetch, if any */
  error: Error | null;
  /** Manually update particle speed */
  setSpeed: (speed: number) => void;
  /** Manually update particle count */
  setParticleCount: (n: number) => void;
}

export function useWindLayer({
  mapRef,
  enabled = true,
  options = {},
  textureParams = {},
}: UseWindLayerParams): UseWindLayerResult {
  const layerRef = useRef<WindLayer | null>(null);
  const addedRef = useRef(false);

  // Fetch wind texture PNG
  const {
    data: windData,
    isLoading,
    error,
  } = useWindTexture(enabled ? textureParams : { bbox: "__disabled__" });

  // Create layer instance (stable across renders)
  const getLayer = useCallback(() => {
    if (!layerRef.current) {
      layerRef.current = new WindLayer({
        id: "wind-particles",
        ...options,
      });
    }
    return layerRef.current;
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Add / remove layer from map
  useEffect(() => {
    const map = mapRef.current?.getMap();
    if (!map) return;

    const layer = getLayer();

    const addLayer = () => {
      if (!addedRef.current && enabled) {
        try {
          // Add below the first symbol layer for correct z-ordering
          const symbolLayer = map
            .getStyle()
            ?.layers?.find((l) => l.type === "symbol");
          map.addLayer(
            layer as unknown as maplibregl.AddLayerObject,
            symbolLayer?.id,
          );
          addedRef.current = true;
        } catch (e) {
          console.warn("[useWindLayer] Failed to add layer:", e);
        }
      }
    };

    // Map may not be fully loaded yet
    if (map.isStyleLoaded()) {
      addLayer();
    } else {
      map.once("styledata", addLayer);
    }

    return () => {
      if (addedRef.current) {
        try {
          map.removeLayer(layer.id);
        } catch {
          // layer may already have been removed
        }
        addedRef.current = false;
      }
    };
  }, [mapRef, enabled, getLayer]);

  // Toggle visibility when enabled changes
  useEffect(() => {
    const map = mapRef.current?.getMap();
    if (!map || !addedRef.current) return;

    try {
      map.setLayoutProperty(
        "wind-particles",
        "visibility",
        enabled ? "visible" : "none",
      );
    } catch {
      // custom layers may not support setLayoutProperty; that is fine
    }
  }, [mapRef, enabled]);

  // Push wind texture data to the layer when it arrives or changes
  useEffect(() => {
    if (!windData || !layerRef.current) return;

    const { imageData, metadata } = windData;

    layerRef.current.setWindTexture(imageData);
    layerRef.current.updateBounds(metadata.bounds);
  }, [windData]);

  // Public imperative methods
  const setSpeed = useCallback((speed: number) => {
    layerRef.current?.setSpeed(speed);
  }, []);

  const setParticleCount = useCallback((n: number) => {
    layerRef.current?.setParticleCount(n);
  }, []);

  return {
    layer: layerRef.current,
    isLoading,
    error: error as Error | null,
    setSpeed,
    setParticleCount,
  };
}
