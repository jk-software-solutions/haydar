import { describe, expect, it } from "vitest";

import {
  coordinatesToWorldPixels,
  isSaudiShortAddress,
  normalizeLocationSearchQuery,
  parseLocationCoordinates,
  roundedCoordinate,
  worldPixelsToCoordinates,
} from "./location-map-utils";

describe("location map utilities", () => {
  it("round-trips Riyadh coordinates through Web Mercator pixels", () => {
    const original = { latitude: 24.7136, longitude: 46.6753 };
    const worldPixels = coordinatesToWorldPixels(original, 14);
    const result = worldPixelsToCoordinates(worldPixels.x, worldPixels.y, 14);

    expect(result.latitude).toBeCloseTo(original.latitude, 6);
    expect(result.longitude).toBeCloseTo(original.longitude, 6);
  });

  it("formats coordinates for branch form submission", () => {
    expect(roundedCoordinate(24.7136004)).toBe("24.713600");
    expect(roundedCoordinate(46.6753006)).toBe("46.675301");
  });

  it("detects and normalizes Saudi short address search", () => {
    expect(isSaudiShortAddress("GGDA3610")).toBe(true);
    expect(isSaudiShortAddress("GGDA-3610")).toBe(false);
    expect(normalizeLocationSearchQuery(" ggda3610 ")).toBe("GGDA3610 Saudi Arabia");
  });

  it("keeps regular place search text normalized", () => {
    expect(normalizeLocationSearchQuery("  King   Fahd   Road  ")).toBe("King Fahd Road");
  });

  it("accepts precise coordinates or a copied Google Maps link", () => {
    expect(parseLocationCoordinates("24.7136, 46.6753")).toEqual({ latitude: 24.7136, longitude: 46.6753 });
    expect(parseLocationCoordinates("https://www.google.com/maps/@24.7136,46.6753,18z")).toEqual({ latitude: 24.7136, longitude: 46.6753 });
    expect(parseLocationCoordinates("91, 46")).toBeNull();
  });
});
