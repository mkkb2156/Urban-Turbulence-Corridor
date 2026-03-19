import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import type { WindTextureMetadata } from "@/api/types";

interface WindTextureParams {
  bbox?: string;
  datetime?: string;
  altitude?: number;
  resolution?: number;
}

interface WindTextureResult {
  imageData: ImageBitmap;
  metadata: WindTextureMetadata;
}

export function useWindTexture(params: WindTextureParams = {}) {
  return useQuery({
    queryKey: ["wind-texture", params],
    queryFn: async (): Promise<WindTextureResult> => {
      const { blob, headers } = await apiClient.getBlob(
        "/wind-texture",
        params as Record<string, unknown>,
      );

      const imageBitmap = await createImageBitmap(blob);

      const metadata: WindTextureMetadata = {
        bounds: (headers.get("X-Wind-Bounds") ?? "121.45,24.96,121.67,25.21")
          .split(",")
          .map(Number) as [number, number, number, number],
        windMin: Number(headers.get("X-Wind-Min") ?? -25),
        windMax: Number(headers.get("X-Wind-Max") ?? 25),
        width: Number(headers.get("X-Wind-Width") ?? 38),
        height: Number(headers.get("X-Wind-Height") ?? 35),
      };

      return { imageData: imageBitmap, metadata };
    },
    staleTime: 300_000,
    refetchInterval: 300_000,
  });
}
