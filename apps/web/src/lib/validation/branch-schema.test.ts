import { describe, expect, it } from "vitest";

import { branchSchema } from "./branch-schema";

describe("branch schema", () => {
  it("normalizes a valid manually located branch", () => {
    const result = branchSchema.parse({
      code: "ruh-01",
      name: " Riyadh Main ",
      saudi_short_address: "",
      full_address: "King Fahd Road",
      latitude: "24.7136",
      longitude: "46.6753",
      geofence_radius_m: "125",
      timezone: "Asia/Riyadh",
    });
    expect(result).toMatchObject({ code: "RUH-01", latitude: 24.7136, geofence_radius_m: 125 });
    expect(result.saudi_short_address).toBeNull();
  });

  it("rejects unsafe geofence and coordinate values", () => {
    const result = branchSchema.safeParse({
      code: "RUH",
      name: "Riyadh",
      saudi_short_address: "",
      full_address: "Address",
      latitude: "100",
      longitude: "46",
      geofence_radius_m: "5",
      timezone: "Asia/Riyadh",
    });
    expect(result.success).toBe(false);
  });
});
