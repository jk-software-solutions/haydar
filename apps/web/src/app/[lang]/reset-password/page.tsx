import { ResetPasswordForm } from "./reset-password-form";

export default async function ResetPasswordPage({
  params,
  searchParams,
}: {
  params: Promise<{ lang: string }>;
  searchParams: Promise<{ token?: string }>;
}) {
  const [{ lang }, query] = await Promise.all([params, searchParams]);
  const ar = lang === "ar";
  return (
    <main className="portal-shell">
      <section className="portal-card">
        <p className="foundation-eyebrow">HADIR | حاضر</p>
        <h1>{ar ? "كلمة مرور جديدة" : "Create a new password"}</h1>
        <p>{ar ? "استخدم رابط الاستعادة الذي وصلك." : "Use the secure reset link delivered to you."}</p>
        <ResetPasswordForm locale={lang} token={query.token ?? ""} />
      </section>
    </main>
  );
}
