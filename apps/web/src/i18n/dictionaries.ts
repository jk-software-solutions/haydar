import "server-only";

import type { Locale } from "./locales";

const dictionaries = {
  ar: () => import("./messages/ar.json").then((module) => module.default),
  en: () => import("./messages/en.json").then((module) => module.default),
};

export type Dictionary = Awaited<ReturnType<(typeof dictionaries)[Locale]>>;

export async function getDictionary(locale: Locale): Promise<Dictionary> {
  return dictionaries[locale]();
}
