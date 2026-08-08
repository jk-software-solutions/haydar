"use client";

import Link from "next/link";
import { useActionState } from "react";

import { loginAction, type LoginState } from "./actions";

const initialState: LoginState = { message: "" };

export function LoginForm({ locale }: { locale: string }) {
  const action = loginAction.bind(null, locale);
  const [state, formAction, pending] = useActionState(action, initialState);
  const ar = locale === "ar";
  return (
    <form action={formAction} className="portal-form">
      <label htmlFor="identifier">{ar ? "البريد الإلكتروني أو الهاتف" : "Email or phone"}</label>
      <input
        id="identifier"
        name="identifier"
        autoComplete="username"
        placeholder={ar ? "name@example.com أو +966..." : "name@example.com or +966..."}
        required
      />
      {state.errors?.identifier?.map((error) => <p className="form-error" key={error}>{error}</p>)}
      <label htmlFor="password">{ar ? "كلمة المرور" : "Password"}</label>
      <input id="password" name="password" type="password" autoComplete="current-password" required />
      {state.errors?.password?.map((error) => <p className="form-error" key={error}>{error}</p>)}
      <p className="form-error" aria-live="polite">{state.message}</p>
      <button type="submit" disabled={pending}>
        {pending ? (ar ? "جارٍ تسجيل الدخول..." : "Signing in...") : (ar ? "تسجيل الدخول" : "Sign in")}
      </button>
      <Link href={`/${locale}/forgot-password`}>
        {ar ? "نسيت كلمة المرور؟" : "Forgot your password?"}
      </Link>
      <Link href={`/${locale}/register`}>
        {ar ? "إنشاء شركة جديدة" : "Create a new company"}
      </Link>
    </form>
  );
}
