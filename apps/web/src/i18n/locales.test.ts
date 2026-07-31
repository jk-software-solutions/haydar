import { describe, expect, it } from "vitest";

import { directionFor, hasLocale, preferredLocale } from "./locales";

describe("locale policy", () => {
  it("is Arabic-first and applies the correct direction", () => {
    expect(preferredLocale(null)).toBe("ar");
    expect(directionFor("ar")).toBe("rtl");
    expect(directionFor("en")).toBe("ltr");
  });

  it("selects English only when requested and rejects unsupported locales", () => {
    expect(preferredLocale("fr-FR, en-US;q=0.8")).toBe("en");
    expect(hasLocale("fr")).toBe(false);
  });
});
