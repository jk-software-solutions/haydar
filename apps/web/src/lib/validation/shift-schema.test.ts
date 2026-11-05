import { describe, expect, it } from "vitest";

import { shiftAssignmentSchema, shiftSchema } from "./shift-schema";

describe("shift schema", () => {
  it("accepts an overnight schedule without client-derived status", () => {
    const result = shiftSchema.parse({
      code: "night",
      name: "Night shift",
      start_time: "22:00",
      end_time: "06:00",
      working_days: ["0", "1", "2"],
      grace_period_minutes: "10",
      checkout_grace_period_minutes: "0",
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

  it("accepts a branch shift assignment", () => {
    const result = shiftAssignmentSchema.parse({
      shift_id: "11111111-1111-4111-8111-111111111111",
      target_type: "branch",
      membership_id: "",
      branch_id: "22222222-2222-4222-8222-222222222222",
      effective_from: "2026-08-12",
      effective_to: "",
    });
    expect(result.membership_id).toBeNull();
    expect(result.branch_id).toBe("22222222-2222-4222-8222-222222222222");
  });

  it("rejects a branch assignment without a branch", () => {
    const result = shiftAssignmentSchema.safeParse({
      shift_id: "11111111-1111-4111-8111-111111111111",
      target_type: "branch",
      membership_id: "",
      branch_id: "",
      effective_from: "2026-08-12",
      effective_to: "",
    });
    expect(result.success).toBe(false);
  });
});
