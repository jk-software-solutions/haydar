"use server";

import { redirect } from "next/navigation";

import { registerCompanyWithApi } from "@/lib/auth/server-session";
import { registrationSchema } from "@/lib/validation/registration-schema";

export type RegistrationState = { message: string; errors?: Record<string, string[]> };

export async function registerCompanyAction(
  locale: string,
  _state: RegistrationState,
  formData: FormData,
): Promise<RegistrationState> {
  const parsed = registrationSchema.safeParse({
    company_name: formData.get("company_name"),
    owner_full_name: formData.get("owner_full_name"),
    owner_email: formData.get("owner_email"),
    password: formData.get("password"),
    confirm_password: formData.get("confirm_password"),
  });
  if (!parsed.success) {
    return { message: "", errors: parsed.error.flatten().fieldErrors };
  }
  try {
    await registerCompanyWithApi({
      company_name: parsed.data.company_name,
      owner_full_name: parsed.data.owner_full_name,
      owner_email: parsed.data.owner_email,
      password: parsed.data.password,
    });
  } catch (error) {
    return { message: error instanceof Error ? error.message : "Registration failed." };
  }
  redirect(`/${locale}/company`);
}
