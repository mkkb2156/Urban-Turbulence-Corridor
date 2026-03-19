import { create } from "zustand";

interface MapState {
  // 視口
  longitude: number;
  latitude: number;
  zoom: number;

  // 選中的點
  selectedPoint: { lng: number; lat: number } | null;

  // Actions
  setViewport: (lng: number, lat: number, zoom: number) => void;
  setSelectedPoint: (point: { lng: number; lat: number } | null) => void;
  flyTo: (lng: number, lat: number, zoom?: number) => void;
}

export const useMapStore = create<MapState>((set) => ({
  longitude: 121.5654,
  latitude: 25.033,
  zoom: 12,

  selectedPoint: null,

  setViewport: (longitude, latitude, zoom) =>
    set({ longitude, latitude, zoom }),

  setSelectedPoint: (selectedPoint) => set({ selectedPoint }),

  flyTo: (longitude, latitude, zoom) =>
    set({ longitude, latitude, zoom: zoom ?? 14 }),
}));
