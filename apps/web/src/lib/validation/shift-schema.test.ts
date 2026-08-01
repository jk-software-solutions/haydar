import { describe, expect, it } from "vitest";

import { shiftSchema } from "./shift-schema";

describe("shift schema", () => {
  it("accepts an overnight schedule without client-derived status", () => {
    const result = shiftSchema.parse({
      code: "night",
      name: "Night shift",
      start_time: "22:00",
      end_time: "06:00",
      working_days: ["0", "1", "2"],
      grace_period_minutes: "10",
      break_duration_minutes: "60",
      effective_from: "2026-08-01",
      effective_to: "",
    });
    expect(result.code).toBe("NIGHT");
    expect(result.effective_to).toBeNull();
    expect(result).not.toHaveProperty("is_overnight");
  });

  it("rejects duplicate workdays", () => {
    const result = shiftSchema.safeParse({
      code: "DAY",
      name: "Day shift",
      start_time: "08:00",
      end_time: "17:00",
      working_days: ["0", "0"],
      grace_period_minutes: "0",
      break_duration_minutes: "0",
      effective_from: "2026-08-01",
      effective_to: "",
    });
    expect(result.success).toBe(false);
  });
});
