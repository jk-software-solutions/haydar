"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { authorizedApiFetch, getWebSession, logoutWithApi } from "@/lib/auth/server-session";
import { invitationSchema } from "@/lib/validation/invitation-schema";

export type InvitationState = {
  message: string;
  activationToken?: string;
  errors?: Record<string, string[]>;
};

export async function logoutAction(locale: string): Promise<void> {
  await logoutWithApi();
  redirect(`/${locale}/login`);
}

export async function createInvitationAction(
  locale: string,
  _state: InvitationState,
  formData: FormData,
): Promise<InvitationState> {
  const session = await getWebSession();
  if (!session || !session.roles.some((role) => ["OWNER", "MANAGER", "HR_OFFICER"].includes(role))) {
    return { message: "Permission denied." };
  }
  const parsed = invitationSchema.safeParse({
    full_name: formData.get("full_name"),
    email: formData.get("email"),
    role_code: formData.get("role_code"),
  });
  if (!parsed.success) {
    return { message: "", errors: parsed.error.flatten().fieldErrors };
  }
  const response = await authorizedApiFetch("/invitations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(parsed.data),
  });
  if (!response.ok) {
    const problem = await response.json().catch(() => ({})) as { detail?: string };
    return { message: problem.detail ?? "Invitation creation failed." };
  }
  const created = await response.json() as { activation_token: string };
  revalidatePath(`/${locale}/company`);
  return {
    message: "Invitation created. Copy the one-time token now.",
    activationToken: created.activation_token,
  };
}
