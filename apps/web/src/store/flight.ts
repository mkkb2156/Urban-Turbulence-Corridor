import { create } from "zustand";
import type { DroneModel } from "@/api/types";
import { DRONE_MODELS } from "@/api/types";

interface FlightState {
  // 機型
  selectedDrone: DroneModel;
  // 時間
  selectedTime: Date;
  // 高度
  altitude: number;

  // Actions
  setDrone: (droneId: string) => void;
  setTime: (time: Date) => void;
  setAltitude: (alt: number) => void;
}

export const useFlightStore = create<FlightState>((set) => ({
  selectedDrone: DRONE_MODELS.find((d) => d.id === "dji-matrice30")!,
  selectedTime: new Date(),
  altitude: 80,

  setDrone: (droneId) => {
    const drone = DRONE_MODELS.find((d) => d.id === droneId);
    if (drone) set({ selectedDrone: drone });
  },

  setTime: (selectedTime) => set({ selectedTime }),

  setAltitude: (altitude) => set({ altitude }),
}));
