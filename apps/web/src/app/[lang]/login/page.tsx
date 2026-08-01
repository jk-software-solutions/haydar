import { redirect } from "next/navigation";

import { getWebSession } from "@/lib/auth/server-session";

import { LoginForm } from "./login-form";

export default async function LoginPage({
  params,
}: {
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;
  if (await getWebSession()) redirect(`/${lang}/company`);
  return (
    <main className="portal-shell">
      <section className="portal-card">
        <p className="foundation-eyebrow">HADIR | حاضر</p>
        <h1>{lang === "ar" ? "تسجيل الدخول" : "Sign in"}</h1>
        <p>
          {lang === "ar"
            ? "استخدم حساب الشركة الحقيقي لفتح بوابة الإدارة."
            : "Use your real company account to open the administration portal."}
        </p>
        <LoginForm locale={lang} />
      </section>
    </main>
  );
}
