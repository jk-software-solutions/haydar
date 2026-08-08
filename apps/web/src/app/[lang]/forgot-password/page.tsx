import { ForgotPasswordForm } from "./forgot-password-form";

export default async function ForgotPasswordPage({
  params,
}: {
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;
  const ar = lang === "ar";
  return (
    <main className="portal-shell">
      <section className="portal-card">
        <p className="foundation-eyebrow">HADIR | حاضر</p>
        <h1>{ar ? "استعادة كلمة المرور" : "Reset your password"}</h1>
        <p>
          {ar
            ? "أدخل بريدك وسنرسل رابطًا آمنًا إذا كان الحساب موجودًا."
            : "Enter your email and we will send a secure link if the account exists."}
        </p>
        <ForgotPasswordForm locale={lang} />
      </section>
    </main>
  );
}
