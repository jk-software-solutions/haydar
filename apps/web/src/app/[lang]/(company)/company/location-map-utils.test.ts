import { describe, expect, it } from "vitest";

import {
  coordinatesToWorldPixels,
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
});
