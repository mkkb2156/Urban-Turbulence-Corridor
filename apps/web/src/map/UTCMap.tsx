import { useCallback, useRef } from "react";
import {
  Map,
  Source,
  Layer,
  NavigationControl,
  ScaleControl,
  type MapRef,
  type MapMouseEvent,
} from "@vis.gl/react-maplibre";
import "maplibre-gl/dist/maplibre-gl.css";

import { DeckGLOverlay } from "./DeckGLOverlay";
import { useMapStore } from "@/store/map";
import { useUIStore } from "@/store/ui";

const TILES_URL = import.meta.env.VITE_TILES_URL ?? "http://localhost:3000";

const OPENFREEMAP_STYLE =
  "https://tiles.openfreemap.org/styles/liberty";

export function UTCMap() {
  const mapRef = useRef<MapRef>(null);
  const { longitude, latitude, zoom, setViewport, setSelectedPoint } =
    useMapStore();
  const layers = useUIStore((s) => s.layers);
  const setFlightPanelOpen = useUIStore((s) => s.setFlightPanelOpen);

  const handleClick = useCallback(
    (e: MapMouseEvent) => {
      const { lng, lat } = e.lngLat;
      setSelectedPoint({ lng, lat });
      setFlightPanelOpen(true);
    },
    [setSelectedPoint, setFlightPanelOpen],
  );

  const handleMove = useCallback(
    (e: { viewState: { longitude: number; latitude: number; zoom: number } }) => {
      setViewport(e.viewState.longitude, e.viewState.latitude, e.viewState.zoom);
    },
    [setViewport],
  );

  // Deck.gl layers (wind particles added in Step 7)
  const deckLayers: never[] = [];

  return (
    <Map
      ref={mapRef}
      mapStyle={OPENFREEMAP_STYLE}
      longitude={longitude}
      latitude={latitude}
      zoom={zoom}
      onMove={handleMove}
      onClick={handleClick}
      style={{ width: "100%", height: "100%" }}
      maxZoom={18}
      minZoom={8}
      attributionControl={false}
    >
      <NavigationControl position="bottom-right" />
      <ScaleControl position="bottom-left" />

      {/* ── Martin MVT: Risk Grid ─────────────────────────── */}
      {layers.riskGrid && (
        <Source
          id="risk_grid"
          type="vector"
          tiles={[`${TILES_URL}/risk_grid/{z}/{x}/{y}`]}
          minzoom={10}
          maxzoom={18}
        >
          <Layer
            id="risk_grid_fill"
            type="fill"
            source-layer="risk_grid"
            paint={{
              "fill-color": [
                "match",
                ["get", "risk_level"],
                "green", "#22c55e",
                "yellow", "#eab308",
                "red", "#ef4444",
                "black", "#1e1e1e",
                "#cccccc",
              ],
              "fill-opacity": 0.45,
            }}
          />
          <Layer
            id="risk_grid_outline"
            type="line"
            source-layer="risk_grid"
            paint={{
              "line-color": "#ffffff",
              "line-width": 0.3,
              "line-opacity": 0.3,
            }}
          />
        </Source>
      )}

      {/* ── Martin MVT: Corridors ─────────────────────────── */}
      {layers.corridors && (
        <Source
          id="corridors"
          type="vector"
          tiles={[`${TILES_URL}/corridors/{z}/{x}/{y}`]}
          minzoom={10}
          maxzoom={18}
        >
          <Layer
            id="corridors_line"
            type="line"
            source-layer="corridors"
            paint={{
              "line-color": "#3b82f6",
              "line-width": 3,
              "line-opacity": 0.7,
            }}
          />
        </Source>
      )}

      {/* ── Martin MVT: Airspace Zones ────────────────────── */}
      {layers.airspace && (
        <Source
          id="airspace"
          type="vector"
          tiles={[`${TILES_URL}/airspace/{z}/{x}/{y}`]}
          minzoom={8}
          maxzoom={18}
        >
          <Layer
            id="airspace_fill"
            type="fill"
            source-layer="airspace"
            paint={{
              "fill-color": "#ef4444",
              "fill-opacity": 0.15,
            }}
          />
          <Layer
            id="airspace_outline"
            type="line"
            source-layer="airspace"
            paint={{
              "line-color": "#ef4444",
              "line-width": 2,
              "line-dasharray": [2, 2],
            }}
          />
        </Source>
      )}

      {/* ── Martin MVT: 3D Buildings ──────────────────────── */}
      {layers.buildings3d && (
        <Source
          id="buildings_3d"
          type="vector"
          tiles={[`${TILES_URL}/buildings_3d/{z}/{x}/{y}`]}
          minzoom={14}
          maxzoom={18}
        >
          <Layer
            id="buildings_3d_extrusion"
            type="fill-extrusion"
            source-layer="buildings_3d"
            paint={{
              "fill-extrusion-color": "#94a3b8",
              "fill-extrusion-height": ["get", "height"],
              "fill-extrusion-base": 0,
              "fill-extrusion-opacity": 0.6,
            }}
          />
        </Source>
      )}

      {/* ── Deck.gl Interleaved Overlay ───────────────────── */}
      <DeckGLOverlay layers={deckLayers} />
    </Map>
  );
}
