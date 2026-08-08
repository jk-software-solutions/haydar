"use server";

import { revalidatePath } from "next/cache";

import { authorizedApiFetch } from "@/lib/auth/server-session";

export type AccessActionState = { message: string; success?: boolean };

export async function updateMemberAccessAction(
  locale: string,
  membershipId: string,
  _state: AccessActionState,
  formData: FormData,
): Promise<AccessActionState> {
  const permissionOverrides: Record<string, boolean> = {};
  for (const [key, value] of formData.entries()) {
    if (!key.startsWith("permission::") || value === "inherit") continue;
    permissionOverrides[key.slice("permission::".length)] = value === "allow";
  }
  const response = await authorizedApiFetch(`/members/${membershipId}/access`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      role_codes: formData.getAll("role_codes").map(String),
      permission_overrides: permissionOverrides,
      branch_ids: formData.getAll("branch_ids").map(String),
      department_ids: formData.getAll("department_ids").map(String),
      group_ids: formData.getAll("group_ids").map(String),
    }),
  });
  if (!response.ok) {
    const problem = (await response.json().catch(() => null)) as { detail?: string } | null;
    return { message: problem?.detail ?? "Access could not be updated." };
  }
  revalidatePath(`/${locale}/company`);
  return {
    message: locale === "ar" ? "تم تحديث الصلاحيات والنطاق." : "Access and scope updated.",
    success: true,
  };
}
