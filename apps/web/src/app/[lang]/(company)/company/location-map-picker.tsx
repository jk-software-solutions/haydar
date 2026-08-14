"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import {
  coordinatesToWorldPixels,
  roundedCoordinate,
  worldPixelsToCoordinates,
  type Coordinates,
} from "./location-map-utils";

const TILE_SIZE = 256;
const DEFAULT_MAP_SIZE = { width: 640, height: 320 };
const DEFAULT_RIYADH: Coordinates = { latitude: 24.7136, longitude: 46.6753 };

type Tile = {
  key: string;
  src: string;
  left: number;
  top: number;
};

function validNumber(value: number | string | undefined): number | null {
  if (value === undefined || value === "") return null;
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function LocationMapPicker({
  locale,
  initialLatitude,
  initialLongitude,
}: {
  locale: string;
  initialLatitude?: number | string;
  initialLongitude?: number | string;
}) {
  const ar = locale === "ar";
  const mapRef = useRef<HTMLDivElement>(null);
  const initialLat = validNumber(initialLatitude);
  const initialLng = validNumber(initialLongitude);
  const [selected, setSelected] = useState<Coordinates>(
    initialLat !== null && initialLng !== null
      ? { latitude: initialLat, longitude: initialLng }
      : DEFAULT_RIYADH,
  );
  const [zoom, setZoom] = useState(14);
  const [message, setMessage] = useState("");
  const [mapSize, setMapSize] = useState(DEFAULT_MAP_SIZE);

  useEffect(() => {
    const element = mapRef.current;
    if (!element) return;
    const updateSize = () => {
      const rect = element.getBoundingClientRect();
      setMapSize({ width: rect.width || DEFAULT_MAP_SIZE.width, height: rect.height || DEFAULT_MAP_SIZE.height });
    };
    updateSize();
    const observer = new ResizeObserver(updateSize);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const centerPixels = useMemo(
    () => coordinatesToWorldPixels(selected, zoom),
    [selected, zoom],
  );
  const tiles = useMemo<Tile[]>(() => {
    const tileCount = 2 ** zoom;
    const centerTileX = Math.floor(centerPixels.x / TILE_SIZE);
    const centerTileY = Math.floor(centerPixels.y / TILE_SIZE);
    const offsetX = mapSize.width / 2 - centerPixels.x;
    const offsetY = mapSize.height / 2 - centerPixels.y;
    const output: Tile[] = [];
    for (let x = centerTileX - 2; x <= centerTileX + 2; x += 1) {
      for (let y = centerTileY - 2; y <= centerTileY + 2; y += 1) {
        if (y < 0 || y >= tileCount) continue;
        const wrappedX = ((x % tileCount) + tileCount) % tileCount;
        output.push({
          key: `${zoom}-${wrappedX}-${y}`,
          src: `https://tile.openstreetmap.org/${zoom}/${wrappedX}/${y}.png`,
          left: x * TILE_SIZE + offsetX,
          top: y * TILE_SIZE + offsetY,
        });
      }
    }
    return output;
  }, [centerPixels, mapSize, zoom]);

  const pickFromPointer = (clientX: number, clientY: number) => {
    const rect = mapRef.current?.getBoundingClientRect();
    if (!rect) return;
    const x = centerPixels.x + (clientX - rect.left - rect.width / 2);
    const y = centerPixels.y + (clientY - rect.top - rect.height / 2);
    const next = worldPixelsToCoordinates(x, y, zoom);
    setSelected(next);
    setMessage(ar ? "تم اختيار الموقع من الخريطة." : "Location selected from the map.");
  };

  const useCurrentLocation = () => {
    if (!navigator.geolocation) {
      setMessage(ar ? "المتصفح لا يدعم تحديد الموقع." : "This browser does not support geolocation.");
      return;
    }
    setMessage(ar ? "جارٍ قراءة موقعك..." : "Reading your current location...");
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setSelected({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        });
        setZoom(16);
        setMessage(ar ? "تم استخدام موقعك الحالي." : "Current location selected.");
      },
      () => {
        setMessage(ar ? "تعذر قراءة الموقع الحالي. اختر الموقع من الخريطة." : "Could not read current location. Pick it on the map.");
      },
      { enableHighAccuracy: true, timeout: 10000 },
    );
  };

  return (
    <section className="location-picker">
      <input name="latitude" type="hidden" value={roundedCoordinate(selected.latitude)} />
      <input name="longitude" type="hidden" value={roundedCoordinate(selected.longitude)} />
      <div className="location-picker-header">
        <div>
          <strong>{ar ? "موقع الفرع على الخريطة" : "Branch location on map"}</strong>
          <span>
            {ar
              ? "اضغط على الخريطة لاختيار موقع الفرع؛ النظام يعبئ الإحداثيات تلقائياً."
              : "Click the map to choose the branch location; coordinates are filled automatically."}
          </span>
        </div>
        <button type="button" onClick={useCurrentLocation}>
          {ar ? "استخدم موقعي" : "Use my location"}
        </button>
      </div>
      <div
        aria-label={ar ? "خريطة اختيار موقع الفرع" : "Branch location picker map"}
        className="location-map"
        onClick={(event) => pickFromPointer(event.clientX, event.clientY)}
        ref={mapRef}
        role="button"
        tabIndex={0}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            const rect = mapRef.current?.getBoundingClientRect();
            if (rect) pickFromPointer(rect.left + rect.width / 2, rect.top + rect.height / 2);
          }
        }}
      >
        {tiles.map((tile) => (
          <span
            aria-hidden="true"
            className="location-map-tile"
            key={tile.key}
            style={{ backgroundImage: `url(${tile.src})`, left: tile.left, top: tile.top }}
          />
        ))}
        <span className="location-map-pin" aria-hidden="true" />
        <div className="location-map-controls" onClick={(event) => event.stopPropagation()}>
          <button type="button" onClick={() => setZoom((value) => Math.min(18, value + 1))}>+</button>
          <button type="button" onClick={() => setZoom((value) => Math.max(3, value - 1))}>−</button>
        </div>
      </div>
      <div className="location-picker-readout">
        <span>{ar ? "خط العرض" : "Latitude"}: {roundedCoordinate(selected.latitude)}</span>
        <span>{ar ? "خط الطول" : "Longitude"}: {roundedCoordinate(selected.longitude)}</span>
      </div>
      <p className="location-picker-hint" aria-live="polite">{message || (ar ? "يمكنك التكبير ثم الضغط على الموقع المطلوب." : "Zoom in, then click the exact location.")}</p>
      <small>
        {ar
          ? "خرائط © OpenStreetMap contributors"
          : "Map data © OpenStreetMap contributors"}
      </small>
    </section>
  );
}
