import { notFound } from "next/navigation";

import { FoundationContent } from "@/components/foundation-content";
import { getDictionary } from "@/i18n/dictionaries";
import { hasLocale } from "@/i18n/locales";

export default async function HomePage({ params }: PageProps<"/[lang]">) {
  const { lang } = await params;
  if (!hasLocale(lang)) notFound();

  return <FoundationContent locale={lang} dictionary={await getDictionary(lang)} />;
}
