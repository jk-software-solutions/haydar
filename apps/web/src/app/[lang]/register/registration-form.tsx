"use client";

import Link from "next/link";
import { useActionState } from "react";

import { registerCompanyAction, type RegistrationState } from "./actions";

const initialState: RegistrationState = { message: "" };

export function RegistrationForm({ locale }: { locale: string }) {
  const [state, action, pending] = useActionState(
    registerCompanyAction.bind(null, locale),
    initialState,
  );
  const ar = locale === "ar";
  const error = (field: string) =>
    state.errors?.[field]?.map((message) => <p className="form-error" key={message}>{message}</p>);
  return (
    <form action={action} className="portal-form">
      <label htmlFor="company_name">{ar ? "اسم الشركة" : "Company name"}</label>
      <input id="company_name" name="company_name" required autoComplete="organization" />
      {error("company_name")}
      <label htmlFor="owner_full_name">{ar ? "اسم مالك الحساب" : "Owner full name"}</label>
      <input id="owner_full_name" name="owner_full_name" required autoComplete="name" />
      {error("owner_full_name")}
      <label htmlFor="owner_email">{ar ? "البريد الإلكتروني" : "Email"}</label>
      <input id="owner_email" name="owner_email" type="email" required autoComplete="email" />
      {error("owner_email")}
      <label htmlFor="password">{ar ? "كلمة المرور" : "Password"}</label>
      <input id="password" name="password" type="password" minLength={8} required autoComplete="new-password" />
      {error("password")}
      <label htmlFor="confirm_password">{ar ? "تأكيد كلمة المرور" : "Confirm password"}</label>
      <input id="confirm_password" name="confirm_password" type="password" minLength={8} required autoComplete="new-password" />
      {error("confirm_password")}
      <p className="form-error" aria-live="polite">{state.message}</p>
      <button type="submit" disabled={pending}>
        {pending ? (ar ? "جارٍ إنشاء الشركة..." : "Creating company...") : (ar ? "إنشاء الشركة" : "Create company")}
      </button>
      <Link href={`/${locale}/login`}>{ar ? "لديك حساب؟ سجل الدخول" : "Already registered? Sign in"}</Link>
    </form>
  );
}
