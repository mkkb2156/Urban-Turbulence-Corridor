import { createContext, useContext, useState, useCallback } from 'react';
import type { HeightOption, DroneModel } from '../api/types';
import { DRONE_MODELS } from '../api/types';

interface FlightState {
  selectedDrone: DroneModel | null;
  selectedHeight: HeightOption;
  currentTime: string | null; // ISO string for timeline
  timeRangeHours: number;
}

interface FlightContextValue extends FlightState {
  setDrone: (drone: DroneModel | null) => void;
  setHeight: (h: HeightOption) => void;
  setCurrentTime: (t: string | null) => void;
  setTimeRange: (hours: number) => void;
}

const FlightContext = createContext<FlightContextValue | null>(null);

export function FlightProvider({ children }: { children: React.ReactNode }) {
  const [selectedDrone, setSelectedDrone] = useState<DroneModel | null>(DRONE_MODELS[0]);
  const [selectedHeight, setSelectedHeight] = useState<HeightOption>(50);
  const [currentTime, setCurrentTime] = useState<string | null>(null);
  const [timeRangeHours, setTimeRangeHours] = useState(72);

  const setDrone = useCallback((drone: DroneModel | null) => setSelectedDrone(drone), []);
  const setHeight = useCallback((h: HeightOption) => setSelectedHeight(h), []);
  const setTime = useCallback((t: string | null) => setCurrentTime(t), []);
  const setTimeRange = useCallback((hours: number) => setTimeRangeHours(hours), []);

  return (
    <FlightContext.Provider
      value={{
        selectedDrone,
        selectedHeight,
        currentTime,
        timeRangeHours,
        setDrone,
        setHeight,
        setCurrentTime: setTime,
        setTimeRange,
      }}
    >
      {children}
    </FlightContext.Provider>
  );
}

export function useFlight() {
  const ctx = useContext(FlightContext);
  if (!ctx) throw new Error('useFlight must be used within FlightProvider');
  return ctx;
}
