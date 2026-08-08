import { redirect } from "next/navigation";

import { getWebSession } from "@/lib/auth/server-session";

import { RegistrationForm } from "./registration-form";

export default async function RegisterPage({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  if (await getWebSession()) redirect(`/${lang}/company`);
  const ar = lang === "ar";
  return (
    <main className="portal-shell">
      <section className="portal-card">
        <p className="foundation-eyebrow">HADIR | حاضر</p>
        <h1>{ar ? "إنشاء شركة" : "Create your company"}</h1>
        <p>{ar ? "ابدأ بفترة تجريبية حقيقية ثم أضف فريقك وفروعك." : "Start a real trial, then add your team and branches."}</p>
        <RegistrationForm locale={lang} />
      </section>
    </main>
  );
}
