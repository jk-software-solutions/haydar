import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { getDictionary } from "@/i18n/dictionaries";
import { directionFor, hasLocale, locales } from "@/i18n/locales";

import "../globals.css";
import { Providers } from "../providers";

export function generateStaticParams() {
  return locales.map((lang) => ({ lang }));
}

export async function generateMetadata({
  params,
}: LayoutProps<"/[lang]">): Promise<Metadata> {
  const { lang } = await params;
  if (!hasLocale(lang)) return {};
  const dictionary = await getDictionary(lang);
  return dictionary.metadata;
}

export default async function LocaleLayout({
  children,
  params,
}: LayoutProps<"/[lang]">) {
  const { lang } = await params;
  if (!hasLocale(lang)) notFound();

  return (
    <html lang={lang} dir={directionFor(lang)}>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
