"use client";

import { PointerEvent, WheelEvent, useEffect, useMemo, useRef, useState } from "react";

import {
  coordinatesToWorldPixels,
  isSaudiShortAddress,
  roundedCoordinate,
  worldPixelsToCoordinates,
  type Coordinates,
} from "./location-map-utils";

const TILE_SIZE = 256;
const DEFAULT_MAP_SIZE = { width: 640, height: 360 };
const DEFAULT_RIYADH: Coordinates = { latitude: 24.7136, longitude: 46.6753 };

type Tile = {
  key: string;
  src: string;
  left: number;
  top: number;
};

type GeocodeResult = {
  id: string;
  label: string;
  latitude: number;
  longitude: number;
  type: string;
};

type DragState = {
  pointerId: number;
  startX: number;
  startY: number;
  startCenter: { x: number; y: number };
  moved: boolean;
};

function validNumber(value: number | string | undefined): number | null {
  if (value === undefined || value === "") return null;
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function resultSummary(result: GeocodeResult): string {
  return `${roundedCoordinate(result.latitude)}, ${roundedCoordinate(result.longitude)}`;
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
  const dragRef = useRef<DragState | null>(null);
  const pendingSelectedRef = useRef<Coordinates | null>(null);
  const animationFrameRef = useRef<number | null>(null);
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
  const [isDragging, setIsDragging] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<GeocodeResult[]>([]);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    const element = mapRef.current;
    if (!element) return;
    const updateSize = () => {
      const rect = element.getBoundingClientRect();
      setMapSize({
        width: rect.width || DEFAULT_MAP_SIZE.width,
        height: rect.height || DEFAULT_MAP_SIZE.height,
      });
    };
    updateSize();
    const observer = new ResizeObserver(updateSize);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  useEffect(() => () => {
    if (animationFrameRef.current !== null) {
      cancelAnimationFrame(animationFrameRef.current);
    }
  }, []);

  const centerPixels = useMemo(
    () => coordinatesToWorldPixels(selected, zoom),
    [selected, zoom],
  );
  const tiles = useMemo<Tile[]>(() => {
    const tileCount = 2 ** zoom;
    const centerTileX = Math.floor(centerPixels.x / TILE_SIZE);
    const centerTileY = Math.floor(centerPixels.y / TILE_SIZE);
    const horizontalTiles = Math.ceil(mapSize.width / TILE_SIZE / 2) + 2;
    const verticalTiles = Math.ceil(mapSize.height / TILE_SIZE / 2) + 2;
    const offsetX = mapSize.width / 2 - centerPixels.x;
    const offsetY = mapSize.height / 2 - centerPixels.y;
    const output: Tile[] = [];
    for (let x = centerTileX - horizontalTiles; x <= centerTileX + horizontalTiles; x += 1) {
      for (let y = centerTileY - verticalTiles; y <= centerTileY + verticalTiles; y += 1) {
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

  const setSelectedFromPointer = (clientX: number, clientY: number) => {
    const rect = mapRef.current?.getBoundingClientRect();
    if (!rect) return;
    const x = centerPixels.x + (clientX - rect.left - rect.width / 2);
    const y = centerPixels.y + (clientY - rect.top - rect.height / 2);
    const next = worldPixelsToCoordinates(x, y, zoom);
    pendingSelectedRef.current = next;
    if (animationFrameRef.current === null) {
      animationFrameRef.current = requestAnimationFrame(() => {
        animationFrameRef.current = null;
        const pending = pendingSelectedRef.current;
        pendingSelectedRef.current = null;
        if (pending) setSelected(pending);
      });
    }
    setMessage(ar ? "تم اختيار الموقع من الخريطة." : "Location selected from the map.");
  };

  const applyResultToForm = (result: GeocodeResult, sourceQuery: string) => {
    const form = mapRef.current?.closest("form");
    const addressInput = form?.elements.namedItem("full_address");
    if (addressInput instanceof HTMLInputElement) {
      addressInput.value = result.label;
    }
    const shortAddressInput = form?.elements.namedItem("saudi_short_address");
    if (shortAddressInput instanceof HTMLInputElement && isSaudiShortAddress(sourceQuery)) {
      shortAddressInput.value = sourceQuery.trim().toUpperCase();
    }
  };

  const selectSearchResult = (result: GeocodeResult) => {
    setSelected({ latitude: result.latitude, longitude: result.longitude });
    setZoom((value) => Math.max(value, 17));
    applyResultToForm(result, searchQuery);
    setMessage(ar ? "تم اختيار نتيجة البحث وتحديث الإحداثيات." : "Search result selected and coordinates updated.");
  };

  const runSearch = async () => {
    const query = searchQuery.trim();
    if (query.length < 2) {
      setMessage(ar ? "اكتب اسم مكان أو رمزاً وطنياً سعودياً." : "Type a place name or Saudi short address.");
      return;
    }
    setSearching(true);
    setSearchResults([]);
    setMessage(ar ? "جارٍ البحث..." : "Searching...");
    try {
      // Nginx reserves /api/* for the FastAPI service. The Next route is
      // intentionally exposed at /geocode so the browser reaches Next.js.
      const response = await fetch(`/geocode?q=${encodeURIComponent(query)}&lang=${locale}`, {
        cache: "no-store",
      });
      if (!response.ok) throw new Error(`geocode_${response.status}`);
      const payload = (await response.json()) as { results?: GeocodeResult[] };
      const results = payload.results ?? [];
      setSearchResults(results);
      setMessage(
        results.length > 0
          ? (ar ? "اختر نتيجة من القائمة أو حرّك الخريطة." : "Choose a result or fine-tune on the map.")
          : (ar ? "لم يتم العثور على نتيجة. جرّب اسم الشارع/المدينة أو اختر من الخريطة." : "No result found. Try street/city text or pick on the map."),
      );
    } catch {
      setMessage(ar ? "تعذر البحث الآن. اختر الموقع من الخريطة." : "Search is unavailable now. Pick the location on the map.");
    } finally {
      setSearching(false);
    }
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
        setZoom(17);
        setMessage(ar ? "تم استخدام موقعك الحالي." : "Current location selected.");
      },
      () => {
        setMessage(ar ? "تعذر قراءة الموقع الحالي. اختر الموقع من الخريطة." : "Could not read current location. Pick it on the map.");
      },
      { enableHighAccuracy: true, timeout: 10000 },
    );
  };

  const handlePointerDown = (event: PointerEvent<HTMLDivElement>) => {
    event.currentTarget.setPointerCapture(event.pointerId);
    dragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      startCenter: centerPixels,
      moved: false,
    };
    setIsDragging(true);
  };

  const handlePointerMove = (event: PointerEvent<HTMLDivElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    const deltaX = event.clientX - drag.startX;
    const deltaY = event.clientY - drag.startY;
    if (Math.abs(deltaX) > 3 || Math.abs(deltaY) > 3) drag.moved = true;
    const next = worldPixelsToCoordinates(
      drag.startCenter.x - deltaX,
      drag.startCenter.y - deltaY,
      zoom,
    );
    setSelected(next);
  };

  const handlePointerUp = (event: PointerEvent<HTMLDivElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    event.currentTarget.releasePointerCapture(event.pointerId);
    dragRef.current = null;
    setIsDragging(false);
    if (animationFrameRef.current !== null) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
    const pending = pendingSelectedRef.current;
    pendingSelectedRef.current = null;
    if (pending) setSelected(pending);
    if (drag.moved) {
      setMessage(ar ? "تم تحديث الموقع بعد تحريك الخريطة." : "Location updated after moving the map.");
    } else {
      setSelectedFromPointer(event.clientX, event.clientY);
    }
  };

  const handleWheel = (event: WheelEvent<HTMLDivElement>) => {
    event.preventDefault();
    setZoom((value) => Math.min(18, Math.max(3, value + (event.deltaY < 0 ? 1 : -1))));
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
              ? "ابحث باسم المكان أو الرمز الوطني، ثم حرّك الخريطة بسلاسة حتى يصبح الدبوس فوق الموقع."
              : "Search by place name or Saudi short address, then drag the map until the pin is on the site."}
          </span>
        </div>
        <button type="button" onClick={useCurrentLocation}>
          {ar ? "استخدم موقعي" : "Use my location"}
        </button>
      </div>
      <div className="location-search">
        <input
          aria-label={ar ? "البحث عن موقع أو رمز وطني سعودي" : "Search place or Saudi short address"}
          onChange={(event) => setSearchQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              void runSearch();
            }
          }}
          placeholder={ar ? "مثال: GGDA3610 أو شارع الملك فهد" : "Example: GGDA3610 or King Fahd Road"}
          value={searchQuery}
        />
        <button type="button" disabled={searching} onClick={() => void runSearch()}>
          {searching ? (ar ? "جارٍ البحث..." : "Searching...") : (ar ? "بحث" : "Search")}
        </button>
      </div>
      {searchResults.length > 0 && (
        <div className="location-search-results">
          {searchResults.map((result) => (
            <button key={result.id} type="button" onClick={() => selectSearchResult(result)}>
              <strong>{result.label}</strong>
              <span>{result.type} · {resultSummary(result)}</span>
            </button>
          ))}
        </div>
      )}
      <div
        aria-label={ar ? "خريطة اختيار موقع الفرع" : "Branch location picker map"}
        className={isDragging ? "location-map dragging" : "location-map"}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={() => {
          dragRef.current = null;
          setIsDragging(false);
        }}
        onWheel={handleWheel}
        ref={mapRef}
        role="application"
        tabIndex={0}
        onKeyDown={(event) => {
          const step = event.shiftKey ? 80 : 30;
          const center = coordinatesToWorldPixels(selected, zoom);
          if (event.key === "+" || event.key === "=") setZoom((value) => Math.min(18, value + 1));
          if (event.key === "-") setZoom((value) => Math.max(3, value - 1));
          if (event.key === "ArrowUp") setSelected(worldPixelsToCoordinates(center.x, center.y - step, zoom));
          if (event.key === "ArrowDown") setSelected(worldPixelsToCoordinates(center.x, center.y + step, zoom));
          if (event.key === "ArrowLeft") setSelected(worldPixelsToCoordinates(center.x - step, center.y, zoom));
          if (event.key === "ArrowRight") setSelected(worldPixelsToCoordinates(center.x + step, center.y, zoom));
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
        <div className="location-map-tools" onPointerDown={(event) => event.stopPropagation()}>
          <button type="button" onClick={() => setZoom((value) => Math.min(18, value + 1))}>+</button>
          <button type="button" onClick={() => setZoom((value) => Math.max(3, value - 1))}>−</button>
          <button type="button" onClick={() => setSelected(DEFAULT_RIYADH)}>{ar ? "الرياض" : "Riyadh"}</button>
        </div>
      </div>
      <div className="location-picker-readout">
        <span>{ar ? "خط العرض" : "Latitude"}: {roundedCoordinate(selected.latitude)}</span>
        <span>{ar ? "خط الطول" : "Longitude"}: {roundedCoordinate(selected.longitude)}</span>
        <span>{ar ? "التكبير" : "Zoom"}: {zoom}</span>
      </div>
      <p className="location-picker-hint" aria-live="polite">
        {message || (ar ? "اسحب الخريطة أو استخدم عجلة الماوس/الأزرار للتكبير." : "Drag the map or use the mouse wheel/buttons to zoom.")}
      </p>
      <small>
        {ar
          ? "خرائط © OpenStreetMap contributors · البحث عبر Nominatim"
          : "Map data © OpenStreetMap contributors · Search by Nominatim"}
      </small>
    </section>
  );
}
