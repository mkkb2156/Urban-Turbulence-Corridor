import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import type { Corridor } from "@/api/types";

export function useCorridors() {
  return useQuery({
    queryKey: ["corridors"],
    queryFn: () =>
      apiClient.get<{ corridors: Corridor[] }>("/corridors").then(
        (r) => r.corridors,
      ),
    staleTime: 3600_000,
  });
}
