"use client";

import { useActionState } from "react";
import Link from "next/link";

import { loginAction, type LoginState } from "./actions";

const initialState: LoginState = { message: "" };

export function LoginForm({ locale }: { locale: string }) {
  const action = loginAction.bind(null, locale);
  const [state, formAction, pending] = useActionState(action, initialState);
  const ar = locale === "ar";
  return (
    <form action={formAction} className="portal-form">
      <label htmlFor="email">{ar ? "البريد الإلكتروني" : "Email"}</label>
      <input id="email" name="email" type="email" autoComplete="email" required />
      {state.errors?.identifier?.map((error) => <p className="form-error" key={error}>{error}</p>)}
      <label htmlFor="password">{ar ? "كلمة المرور" : "Password"}</label>
      <input id="password" name="password" type="password" autoComplete="current-password" required />
      {state.errors?.password?.map((error) => <p className="form-error" key={error}>{error}</p>)}
      <p className="form-error" aria-live="polite">{state.message}</p>
      <button type="submit" disabled={pending}>{pending ? (ar ? "جارٍ الدخول..." : "Signing in...") : (ar ? "تسجيل الدخول" : "Sign in")}</button>
      <Link href={`/${locale}/forgot-password`}>
        {ar ? "نسيت كلمة المرور؟" : "Forgot your password?"}
      </Link>
    </form>
  );
}
