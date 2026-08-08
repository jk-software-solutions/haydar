"use server";

import { revalidatePath } from "next/cache";

import { authorizedApiFetch, getWebSession } from "@/lib/auth/server-session";

export type GroupActionState = { message: string; success?: boolean };

function text(formData: FormData, key: string): string {
  return String(formData.get(key) ?? "").trim();
}

async function canManageGroups(): Promise<boolean> {
  return Boolean((await getWebSession())?.permissions.includes("departments:manage"));
}

async function resultState(response: Response, locale: string, success: string): Promise<GroupActionState> {
  if (!response.ok) {
    const problem = await response.json().catch(() => ({})) as { detail?: string };
    return { message: problem.detail ?? (locale === "ar" ? "تعذر حفظ المجموعة." : "Group update failed.") };
  }
  revalidatePath(`/${locale}/company`);
  return { message: success, success: true };
}

export async function createGroupAction(
  locale: string,
  _state: GroupActionState,
  formData: FormData,
): Promise<GroupActionState> {
  if (!(await canManageGroups())) return { message: locale === "ar" ? "ليس لديك صلاحية." : "Permission denied." };
  const response = await authorizedApiFetch("/groups", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      code: text(formData, "code").toUpperCase(),
      name: text(formData, "name"),
      description: text(formData, "description"),
    }),
  });
  return resultState(response, locale, locale === "ar" ? "تم إنشاء المجموعة." : "Group created.");
}

export async function updateGroupAction(
  locale: string,
  groupId: string,
  _state: GroupActionState,
  formData: FormData,
): Promise<GroupActionState> {
  if (!(await canManageGroups())) return { message: locale === "ar" ? "ليس لديك صلاحية." : "Permission denied." };
  const response = await authorizedApiFetch(`/groups/${groupId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      version: Number(text(formData, "version")),
      name: text(formData, "name"),
      description: text(formData, "description"),
      is_active: text(formData, "is_active") === "true",
    }),
  });
  return resultState(response, locale, locale === "ar" ? "تم تحديث المجموعة." : "Group updated.");
}

export async function replaceGroupMembersAction(
  locale: string,
  groupId: string,
  _state: GroupActionState,
  formData: FormData,
): Promise<GroupActionState> {
  if (!(await canManageGroups())) return { message: locale === "ar" ? "ليس لديك صلاحية." : "Permission denied." };
  const response = await authorizedApiFetch(`/groups/${groupId}/members`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ membership_ids: formData.getAll("membership_ids").map(String) }),
  });
  return resultState(response, locale, locale === "ar" ? "تم تحديث أعضاء المجموعة." : "Group members updated.");
}
