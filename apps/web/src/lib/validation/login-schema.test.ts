import { describe, expect, it } from "vitest";

import { loginSchema } from "./login-schema";

describe("loginSchema", () => {
  it("accepts a normalized identifier and sufficiently long password", () => {
    expect(
      loginSchema.parse({ identifier: " owner@example.com ", password: "secure-pass" }),
    ).toEqual({ identifier: "owner@example.com", password: "secure-pass" });
  });

  it("rejects short passwords", () => {
    expect(loginSchema.safeParse({ identifier: "user", password: "short" }).success).toBe(false);
  });
});
