"use client";

import { useActionState } from "react";

import { createInvitationAction, resendInvitationCodeAction, type InvitationState } from "./actions";

const initialState: InvitationState = { message: "" };

export function InvitationForm({ locale }: { locale: string }) {
  const ar = locale === "ar";
  const action = createInvitationAction.bind(null, locale);
  const [state, formAction, pending] = useActionState(action, initialState);
  return (
    <form action={formAction} className="portal-form inline">
      <input name="full_name" placeholder={ar ? "الاسم الكامل" : "Full name"} required />
      <input name="email" type="email" placeholder={ar ? "البريد الإلكتروني" : "Email"} required />
      <select name="role_code" defaultValue="EMPLOYEE">
        <option value="EMPLOYEE">{ar ? "موظف" : "Employee"}</option>
        <option value="SUPERVISOR">{ar ? "مشرف" : "Supervisor"}</option>
        <option value="HR_OFFICER">{ar ? "موارد بشرية" : "HR Officer"}</option>
        <option value="MANAGER">{ar ? "مدير" : "Manager"}</option>
      </select>
      <button type="submit" disabled={pending}>{pending ? (ar ? "جارٍ الإنشاء..." : "Creating...") : (ar ? "إنشاء دعوة" : "Create invitation")}</button>
      <p className={state.success ? "form-success" : "form-error"} aria-live="polite">{state.message}</p>
      {state.activationToken && <div className="activation-token"><strong>{ar ? "رمز التفعيل لمرة واحدة" : "One-time activation token"}</strong><code>{state.activationToken}</code></div>}
    </form>
  );
}

export function InvitationCodeAction({
  locale,
  invitationId,
  status,
}: {
  locale: string;
  invitationId: string;
  status: string;
}) {
  const ar = locale === "ar";
  const action = resendInvitationCodeAction.bind(null, locale, invitationId);
  const [state, formAction, pending] = useActionState(action, initialState);
  if (status !== "pending") {
    return <span>{ar ? "لا يمكن إنشاء كود بعد قبول الدعوة" : "Code unavailable after acceptance"}</span>;
  }
  return (
    <form action={formAction} className="invitation-code-action">
      <button type="submit" disabled={pending}>
        {pending ? (ar ? "جارٍ إنشاء الكود..." : "Generating code...") : (ar ? "إعادة إنشاء/نسخ الكود" : "Resend / copy code")}
      </button>
      <p className={state.success ? "form-success" : "form-error"} aria-live="polite">{state.message}</p>
      {state.activationToken && (
        <div className="activation-token compact">
          <strong>{ar ? "كود الدعوة الجديد" : "New invitation code"}</strong>
          <code>{state.activationToken}</code>
        </div>
      )}
    </form>
  );
}
