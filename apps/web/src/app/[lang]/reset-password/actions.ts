"use server";

import { redirect } from "next/navigation";

import { apiBaseUrl } from "@/lib/auth/server-session";

export type ResetPasswordState = { message: string };

export async function confirmPasswordResetAction(
  locale: string,
  _state: ResetPasswordState,
  formData: FormData,
): Promise<ResetPasswordState> {
  const token = String(formData.get("token") ?? "");
  const newPassword = String(formData.get("new_password") ?? "");
  const confirmation = String(formData.get("password_confirmation") ?? "");
  if (token.length < 32) return { message: "The reset token is incomplete." };
  if (newPassword.length < 8) return { message: "Password must be at least 8 characters." };
  if (newPassword !== confirmation) return { message: "Passwords do not match." };
  try {
    const response = await fetch(`${apiBaseUrl}/auth/password-reset/confirm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, new_password: newPassword }),
      cache: "no-store",
    });
    if (!response.ok) {
      const problem = (await response.json().catch(() => null)) as { detail?: string } | null;
      return { message: problem?.detail ?? "The reset link is invalid or expired." };
    }
  } catch {
    return { message: "The reset service is temporarily unavailable." };
  }
  redirect(`/${locale}/login?password_reset=success`);
}
