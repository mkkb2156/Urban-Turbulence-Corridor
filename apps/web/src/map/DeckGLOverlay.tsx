import { useControl } from "@vis.gl/react-maplibre";
import { MapboxOverlay } from "@deck.gl/mapbox";
import type { Layer } from "@deck.gl/core";

interface DeckGLOverlayProps {
  layers: Layer[];
}

export function DeckGLOverlay({ layers }: DeckGLOverlayProps) {
  const overlay = useControl<MapboxOverlay>(
    () => new MapboxOverlay({ interleaved: true }),
  );
  overlay.setProps({ layers });
  return null;
}
