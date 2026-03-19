import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import type { FlightSummary } from "@/api/types";

interface FlightSummaryParams {
  lat: number;
  lng: number;
  drone: string;
  datetime?: string;
  altitude?: number;
}

export function useFlightSummary(params: FlightSummaryParams | null) {
  return useQuery({
    queryKey: ["flight-summary", params],
    queryFn: () =>
      apiClient.get<FlightSummary>("/flight-summary", {
        lat: params!.lat,
        lng: params!.lng,
        drone: params!.drone,
        datetime: params!.datetime,
        altitude: params!.altitude,
      }),
    enabled: params !== null,
    staleTime: 60_000,
    refetchInterval: 300_000,
  });
}
