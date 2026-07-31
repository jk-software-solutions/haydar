import Link from "next/link";

import type { Dictionary } from "@/i18n/dictionaries";
import type { Locale } from "@/i18n/locales";

type FoundationContentProps = {
  locale: Locale;
  dictionary: Dictionary;
};

export function FoundationContent({ locale, dictionary }: FoundationContentProps) {
  const oppositeLocale = locale === "ar" ? "en" : "ar";
  const items = [
    dictionary.foundation.api,
    dictionary.foundation.mobile,
    dictionary.foundation.portal,
  ];

  return (
    <main className="foundation-shell">
      <section className="foundation-card" aria-labelledby="foundation-title">
        <div className="foundation-mark" aria-hidden="true">
          ح
        </div>
        <p className="foundation-eyebrow">{dictionary.foundation.eyebrow}</p>
        <h1 id="foundation-title">{dictionary.foundation.title}</h1>
        <p className="foundation-description">{dictionary.foundation.description}</p>

        <div className="foundation-status" role="status">
          <span className="foundation-pulse" aria-hidden="true" />
          {dictionary.foundation.status}
        </div>

        <ul className="foundation-grid">
          {items.map((item) => (
            <li key={item}>
              <span aria-hidden="true">✓</span>
              {item}
            </li>
          ))}
        </ul>

        <Link className="language-link" href={`/${oppositeLocale}`} hrefLang={oppositeLocale}>
          {dictionary.foundation.language}
        </Link>
      </section>
    </main>
  );
}
