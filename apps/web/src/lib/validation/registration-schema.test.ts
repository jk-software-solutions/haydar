import { describe, expect, it } from "vitest";

import { registrationSchema } from "./registration-schema";

describe("registrationSchema", () => {
  it("normalizes a valid company registration", () => {
    const result = registrationSchema.parse({
      company_name: "  Acme Operations ",
      owner_full_name: "  Owner Name ",
      owner_email: "owner@example.com",
      password: "ChangeMe123!",
      confirm_password: "ChangeMe123!",
    });
    expect(result.company_name).toBe("Acme Operations");
  });

  it("rejects mismatched passwords", () => {
    const result = registrationSchema.safeParse({
      company_name: "Acme",
      owner_full_name: "Owner Name",
      owner_email: "owner@example.com",
      password: "ChangeMe123!",
      confirm_password: "Different123!",
    });
    expect(result.success).toBe(false);
  });
});
