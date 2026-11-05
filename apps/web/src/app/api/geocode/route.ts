import { normalizeLocationSearchQuery } from "@/app/[lang]/(company)/company/location-map-utils";

type NominatimPlace = {
  place_id?: number;
  osm_id?: number;
  display_name?: string;
  lat?: string;
  lon?: string;
  type?: string;
  importance?: number;
};

type GeocodeResult = {
  id: string;
  label: string;
  latitude: number;
  longitude: number;
  type: string;
  importance: number;
};

function cleanLanguage(value: string | null): string {
  if (value === "ar") return "ar";
  return "en";
}

function placeToResult(place: NominatimPlace): GeocodeResult | null {
  const latitude = Number(place.lat);
  const longitude = Number(place.lon);
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude) || !place.display_name) {
    return null;
  }
  return {
    id: String(place.place_id ?? place.osm_id ?? `${place.lat},${place.lon}`),
    label: place.display_name,
    latitude,
    longitude,
    type: place.type ?? "place",
    importance: place.importance ?? 0,
  };
}

export async function GET(request: Request) {
  const url = new URL(request.url);
  const rawQuery = url.searchParams.get("q") ?? "";
  const query = normalizeLocationSearchQuery(rawQuery);
  if (query.length < 2) {
    return Response.json({ results: [] satisfies GeocodeResult[] });
  }

  const language = cleanLanguage(url.searchParams.get("lang"));
  const queryAttempts = Array.from(
    new Set([
      query,
      `${rawQuery.trim()} Saudi Arabia`,
      `${rawQuery.trim()} Saudi National Address`,
      `${rawQuery.trim()} السعودية`,
    ].filter((item) => item.trim().length >= 2)),
  );
  const found = new Map<string, GeocodeResult>();
  for (const attemptedQuery of queryAttempts) {
    const upstreamUrl = new URL("https://nominatim.openstreetmap.org/search");
    upstreamUrl.searchParams.set("format", "jsonv2");
    upstreamUrl.searchParams.set("addressdetails", "1");
    upstreamUrl.searchParams.set("limit", "6");
    upstreamUrl.searchParams.set("countrycodes", "sa");
    upstreamUrl.searchParams.set("accept-language", language);
    upstreamUrl.searchParams.set("q", attemptedQuery);

    const upstream = await fetch(upstreamUrl, {
      headers: {
        Accept: "application/json",
        "Accept-Language": language,
        "User-Agent": "HADIR branch location picker/0.1 (https://2-28-31-153.sslip.io)",
      },
      cache: "no-store",
    });
    if (!upstream.ok) {
      return Response.json(
        { error: "geocode_unavailable", results: [] satisfies GeocodeResult[] },
        { status: 502 },
      );
    }
    const payload = (await upstream.json()) as NominatimPlace[];
    for (const result of payload.map(placeToResult)) {
      if (result !== null) found.set(result.id, result);
    }
    if (found.size > 0) break;
  }
  const results = Array.from(found.values()).sort((a, b) => b.importance - a.importance);

  return Response.json({ results });
}
