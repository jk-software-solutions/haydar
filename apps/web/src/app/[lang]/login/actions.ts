"use server";

import { redirect } from "next/navigation";

import { loginSchema } from "@/lib/validation/login-schema";
import { loginWithApi } from "@/lib/auth/server-session";

export type LoginState = { message: string; errors?: Record<string, string[]> };

export async function loginAction(
  locale: string,
  _state: LoginState,
  formData: FormData,
): Promise<LoginState> {
  const parsed = loginSchema.safeParse({
    identifier: formData.get("email"),
    password: formData.get("password"),
  });
  if (!parsed.success) {
    return { message: "", errors: parsed.error.flatten().fieldErrors };
  }
  try {
    await loginWithApi(parsed.data.identifier, parsed.data.password);
  } catch (error) {
    return { message: error instanceof Error ? error.message : "Login failed." };
  }
  redirect(`/${locale}/company`);
}
