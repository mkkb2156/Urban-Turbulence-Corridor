/**
 * Wind texture PNG decode utilities.
 *
 * PNG 格式：R=U, G=V, 正規化至 0-255
 * 解碼公式：value = pixel / 255 * (max - min) + min
 */

export function decodeWindValue(
  pixel: number,
  min: number,
  max: number,
): number {
  return (pixel / 255) * (max - min) + min;
}

/**
 * 從 ImageData 取得指定像素的 U/V 風速。
 */
export function getWindAtPixel(
  imageData: ImageData,
  x: number,
  y: number,
  windMin: number,
  windMax: number,
): { u: number; v: number; speed: number; direction: number } {
  const idx = (y * imageData.width + x) * 4;
  const rVal = imageData.data[idx] ?? 128;
  const gVal = imageData.data[idx + 1] ?? 128;

  const u = decodeWindValue(rVal, windMin, windMax);
  const v = decodeWindValue(gVal, windMin, windMax);
  const speed = Math.sqrt(u * u + v * v);
  const direction = (Math.atan2(-u, -v) * 180) / Math.PI + 180;

  return { u, v, speed, direction };
}

/**
 * 從經緯度轉換為 texture 像素座標。
 */
export function lngLatToPixel(
  lng: number,
  lat: number,
  bounds: [number, number, number, number],
  width: number,
  height: number,
): { x: number; y: number } {
  const [lngMin, latMin, lngMax, latMax] = bounds;
  const x = Math.floor(((lng - lngMin) / (lngMax - lngMin)) * width);
  const y = Math.floor(((latMax - lat) / (latMax - latMin)) * height);
  return {
    x: Math.max(0, Math.min(width - 1, x)),
    y: Math.max(0, Math.min(height - 1, y)),
  };
}
