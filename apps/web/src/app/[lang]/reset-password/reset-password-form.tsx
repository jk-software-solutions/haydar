"use client";

import { useActionState } from "react";

import { confirmPasswordResetAction, type ResetPasswordState } from "./actions";

export function ResetPasswordForm({ locale, token }: { locale: string; token: string }) {
  const ar = locale === "ar";
  const action = confirmPasswordResetAction.bind(null, locale);
  const [state, formAction, pending] = useActionState<ResetPasswordState, FormData>(
    action,
    { message: "" },
  );
  return (
    <form action={formAction} className="portal-form">
      <input name="token" type="hidden" value={token} />
      <label htmlFor="new-password">{ar ? "كلمة المرور الجديدة" : "New password"}</label>
      <input id="new-password" name="new_password" type="password" autoComplete="new-password" minLength={8} required />
      <label htmlFor="password-confirmation">{ar ? "تأكيد كلمة المرور" : "Confirm password"}</label>
      <input id="password-confirmation" name="password_confirmation" type="password" autoComplete="new-password" minLength={8} required />
      <p className="form-error" aria-live="polite">{state.message}</p>
      <button type="submit" disabled={pending || token.length < 32}>
        {pending
          ? ar ? "جارٍ الحفظ..." : "Saving..."
          : ar ? "حفظ كلمة المرور" : "Save password"}
      </button>
    </form>
  );
}
