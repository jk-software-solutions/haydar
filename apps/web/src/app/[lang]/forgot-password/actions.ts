"use server";

import { apiBaseUrl } from "@/lib/auth/server-session";

export type ForgotPasswordState = { message: string; error?: boolean };

export async function requestPasswordResetAction(
  _locale: string,
  _state: ForgotPasswordState,
  formData: FormData,
): Promise<ForgotPasswordState> {
  const email = String(formData.get("email") ?? "").trim().toLowerCase();
  if (!email.includes("@") || email.length > 320) {
    return { message: "Enter a valid email address.", error: true };
  }
  try {
    const response = await fetch(`${apiBaseUrl}/auth/password-reset/request`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
      cache: "no-store",
    });
    if (!response.ok) throw new Error("request_failed");
    return {
      message: "If the account exists, password reset instructions will be delivered.",
    };
  } catch {
    return { message: "The reset service is temporarily unavailable.", error: true };
  }
}
