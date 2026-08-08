"use client";

import Link from "next/link";
import { useActionState } from "react";

import { requestPasswordResetAction, type ForgotPasswordState } from "./actions";

export function ForgotPasswordForm({ locale }: { locale: string }) {
  const ar = locale === "ar";
  const action = requestPasswordResetAction.bind(null, locale);
  const [state, formAction, pending] = useActionState<ForgotPasswordState, FormData>(
    action,
    { message: "" },
  );
  return (
    <form action={formAction} className="portal-form">
      <label htmlFor="reset-email">{ar ? "البريد الإلكتروني" : "Email"}</label>
      <input id="reset-email" name="email" type="email" autoComplete="email" required />
      {state.message && (
        <p className={state.error ? "form-error" : "form-success"} aria-live="polite">
          {ar && !state.error
            ? "إذا كان الحساب موجودًا، فستصل تعليمات إعادة التعيين."
            : state.message}
        </p>
      )}
      <button type="submit" disabled={pending}>
        {pending
          ? ar ? "جارٍ الإرسال..." : "Sending..."
          : ar ? "إرسال تعليمات الاستعادة" : "Send reset instructions"}
      </button>
      <Link href={`/${locale}/login`}>{ar ? "العودة لتسجيل الدخول" : "Back to sign in"}</Link>
    </form>
  );
}
