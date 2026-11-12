export type Coordinates = {
  latitude: number;
  longitude: number;
};

const TILE_SIZE = 256;
const MAX_LATITUDE = 85.05112878;

export function clampLatitude(latitude: number): number {
  return Math.min(MAX_LATITUDE, Math.max(-MAX_LATITUDE, latitude));
}

export function normalizeLongitude(longitude: number): number {
  return ((((longitude + 180) % 360) + 360) % 360) - 180;
}

export function coordinatesToWorldPixels(
  { latitude, longitude }: Coordinates,
  zoom: number,
): { x: number; y: number } {
  const sinLatitude = Math.sin((clampLatitude(latitude) * Math.PI) / 180);
  const scale = TILE_SIZE * 2 ** zoom;
  return {
    x: ((normalizeLongitude(longitude) + 180) / 360) * scale,
    y:
      (0.5 - Math.log((1 + sinLatitude) / (1 - sinLatitude)) / (4 * Math.PI)) *
      scale,
  };
}

export function worldPixelsToCoordinates(
  x: number,
  y: number,
  zoom: number,
): Coordinates {
  const scale = TILE_SIZE * 2 ** zoom;
  const longitude = (x / scale) * 360 - 180;
  const latitude =
    (180 / Math.PI) *
    Math.atan(Math.sinh(Math.PI * (1 - (2 * y) / scale)));
  return {
    latitude: clampLatitude(latitude),
    longitude: normalizeLongitude(longitude),
  };
}

export function roundedCoordinate(value: number): string {
  return value.toFixed(6);
}

export function parseLocationCoordinates(value: string): Coordinates | null {
  const query = value.trim();
  const match = /^([+-]?\d+(?:\.\d+)?)\s*,\s*([+-]?\d+(?:\.\d+)?)$/.exec(query)
    ?? /google\.[^/]+\/maps\/@([+-]?\d+(?:\.\d+)?),([+-]?\d+(?:\.\d+)?)/i.exec(query);
  if (!match) return null;
  const latitude = Number(match[1]);
  const longitude = Number(match[2]);
  if (Math.abs(latitude) > 90 || Math.abs(longitude) > 180) return null;
  return { latitude, longitude };
}

export function isSaudiShortAddress(value: string): boolean {
  return /^[A-Z]{4}\d{4}$/i.test(value.trim());
}

export function normalizeLocationSearchQuery(value: string): string {
  const query = value.trim().replace(/\s+/g, " ");
  if (!query) return "";
  return isSaudiShortAddress(query) ? `${query.toUpperCase()} Saudi Arabia` : query;
}
