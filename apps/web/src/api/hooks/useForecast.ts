import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import type { ForecastResponse } from "@/api/types";

export function useForecast(city = "taipei") {
  return useQuery({
    queryKey: ["forecast", city],
    queryFn: () => apiClient.get<ForecastResponse>("/forecast", { city }),
    staleTime: 600_000,
  });
}
