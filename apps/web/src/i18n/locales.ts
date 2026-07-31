export const locales = ["ar", "en"] as const;
export const defaultLocale: Locale = "ar";

export type Locale = (typeof locales)[number];

export function hasLocale(value: string): value is Locale {
  return locales.includes(value as Locale);
}

export function directionFor(locale: Locale): "rtl" | "ltr" {
  return locale === "ar" ? "rtl" : "ltr";
}

export function preferredLocale(acceptLanguage: string | null): Locale {
  const preferences = (acceptLanguage ?? "")
    .toLowerCase()
    .split(",")
    .map((entry) => entry.trim().split(";")[0]);

  return preferences.some((entry) => entry === "en" || entry.startsWith("en-"))
    ? "en"
    : defaultLocale;
}
