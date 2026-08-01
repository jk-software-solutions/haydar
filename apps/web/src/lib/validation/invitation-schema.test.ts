import { describe, expect, it } from "vitest";

import { invitationSchema } from "./invitation-schema";

describe("invitationSchema", () => {
  it("normalizes a valid employee invitation", () => {
    expect(
      invitationSchema.parse({
        full_name: "  Hadir Employee  ",
        email: "EMPLOYEE@EXAMPLE.COM",
        role_code: "EMPLOYEE",
      }),
    ).toEqual({
      full_name: "Hadir Employee",
      email: "employee@example.com",
      role_code: "EMPLOYEE",
    });
  });

  it("rejects owner invitations and unknown tenant fields", () => {
    expect(
      invitationSchema.safeParse({
        full_name: "Hadir Owner",
        email: "owner@example.com",
        role_code: "OWNER",
        company_id: "another-company",
      }).success,
    ).toBe(false);
  });
});
