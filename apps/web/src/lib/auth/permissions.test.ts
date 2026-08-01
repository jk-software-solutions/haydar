import { describe, expect, it } from "vitest";

import { canEnterCompanyPortal, canEnterPlatformPortal } from "./permissions";

describe("portal role boundaries", () => {
  it("keeps employees and platform operators out of the company admin portal", () => {
    expect(canEnterCompanyPortal("EMPLOYEE")).toBe(false);
    expect(canEnterCompanyPortal("SUPER_ADMIN")).toBe(false);
    expect(canEnterCompanyPortal("MANAGER")).toBe(true);
  });

  it("allows only SUPER_ADMIN into the platform portal", () => {
    expect(canEnterPlatformPortal("SUPER_ADMIN")).toBe(true);
    expect(canEnterPlatformPortal("OWNER")).toBe(false);
  });
});
