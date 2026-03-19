import { create } from "zustand";
import type { MapLayerVisibility } from "@/api/types";
import { DEFAULT_LAYER_VISIBILITY } from "@/api/types";

interface UIState {
  // 面板
  flightPanelOpen: boolean;
  layerDrawerOpen: boolean;

  // 圖層
  layers: MapLayerVisibility;

  // Actions
  setFlightPanelOpen: (open: boolean) => void;
  setLayerDrawerOpen: (open: boolean) => void;
  toggleLayer: (layer: keyof MapLayerVisibility) => void;
  setLayers: (layers: Partial<MapLayerVisibility>) => void;
}

export const useUIStore = create<UIState>((set) => ({
  flightPanelOpen: false,
  layerDrawerOpen: false,
  layers: DEFAULT_LAYER_VISIBILITY,

  setFlightPanelOpen: (flightPanelOpen) => set({ flightPanelOpen }),
  setLayerDrawerOpen: (layerDrawerOpen) => set({ layerDrawerOpen }),

  toggleLayer: (layer) =>
    set((state) => ({
      layers: { ...state.layers, [layer]: !state.layers[layer] },
    })),

  setLayers: (partial) =>
    set((state) => ({
      layers: { ...state.layers, ...partial },
    })),
}));
