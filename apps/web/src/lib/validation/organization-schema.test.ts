import { describe, expect, it } from "vitest";

import { companySettingsSchema, employeeProfileSchema } from "./organization-schema";

describe("organization schemas", () => {
  it("normalizes editable employee fields", () => {
    const result = employeeProfileSchema.parse({
      version: "2",
      display_name: "  Ahmed Ali  ",
      employee_number: "",
      phone: "+966500000001",
      job_title: "  Supervisor ",
      employment_type: "full_time",
      preferred_locale: "ar",
      attendance_enabled: "on",
    });
    expect(result).toMatchObject({
      version: 2,
      display_name: "Ahmed Ali",
      employee_number: null,
      attendance_enabled: true,
    });
  });

  it("requires a valid two-letter company country code", () => {
    const result = companySettingsSchema.safeParse({
      version: "1",
      display_name: "My Company",
      default_locale: "ar",
      timezone: "Asia/Riyadh",
      country_code: "Saudi Arabia",
      attendance_biometric_policy: "optional",
    });
    expect(result.success).toBe(false);
  });

  it("accepts only an explicit biometric policy", () => {
    const valid = companySettingsSchema.parse({
      version: "3",
      display_name: "My Company",
      default_locale: "en",
      timezone: "Asia/Riyadh",
      country_code: "sa",
      attendance_biometric_policy: "required",
    });
    expect(valid.attendance_biometric_policy).toBe("required");
    expect(valid.country_code).toBe("SA");
  });
});
