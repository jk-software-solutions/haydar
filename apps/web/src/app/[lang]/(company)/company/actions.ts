"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { authorizedApiFetch, getWebSession, logoutWithApi } from "@/lib/auth/server-session";
import { branchSchema } from "@/lib/validation/branch-schema";
import { invitationSchema } from "@/lib/validation/invitation-schema";
import { companySettingsSchema, employeeProfileSchema } from "@/lib/validation/organization-schema";
import { shiftSchema } from "@/lib/validation/shift-schema";

export type InvitationState = {
  message: string;
  activationToken?: string;
  errors?: Record<string, string[]>;
};

export type OrganizationActionState = {
  message: string;
  success?: boolean;
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

export async function updateEmployeeAction(
  locale: string,
  membershipId: string,
  _state: OrganizationActionState,
  formData: FormData,
): Promise<OrganizationActionState> {
  const session = await getWebSession();
  if (!session || !session.roles.some((role) => ["OWNER", "MANAGER", "HR_OFFICER"].includes(role))) {
    return { message: locale === "ar" ? "ليس لديك صلاحية." : "Permission denied." };
  }
  const parsed = employeeProfileSchema.safeParse({
    version: formData.get("version"),
    display_name: formData.get("display_name"),
    employee_number: formData.get("employee_number"),
    phone: formData.get("phone"),
    job_title: formData.get("job_title"),
    employment_type: formData.get("employment_type"),
    preferred_locale: formData.get("preferred_locale"),
    attendance_enabled: formData.get("attendance_enabled"),
  });
  if (!parsed.success) {
    return { message: "", errors: parsed.error.flatten().fieldErrors };
  }
  const response = await authorizedApiFetch(`/employees/${membershipId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(parsed.data),
  });
  if (!response.ok) {
    const problem = await response.json().catch(() => ({})) as { detail?: string };
    return { message: problem.detail ?? (locale === "ar" ? "تعذر حفظ الموظف." : "Employee update failed.") };
  }
  revalidatePath(`/${locale}/company`);
  return { message: locale === "ar" ? "تم حفظ ملف الموظف." : "Employee profile saved.", success: true };
}

export async function updateCompanySettingsAction(
  locale: string,
  _state: OrganizationActionState,
  formData: FormData,
): Promise<OrganizationActionState> {
  const session = await getWebSession();
  if (!session || !session.roles.includes("OWNER")) {
    return { message: locale === "ar" ? "ليس لديك صلاحية." : "Permission denied." };
  }
  const parsed = companySettingsSchema.safeParse({
    version: formData.get("version"),
    display_name: formData.get("display_name"),
    default_locale: formData.get("default_locale"),
    timezone: formData.get("timezone"),
    country_code: formData.get("country_code"),
  });
  if (!parsed.success) {
    return { message: "", errors: parsed.error.flatten().fieldErrors };
  }
  const response = await authorizedApiFetch("/companies/current", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(parsed.data),
  });
  if (!response.ok) {
    const problem = await response.json().catch(() => ({})) as { detail?: string };
    return { message: problem.detail ?? (locale === "ar" ? "تعذر حفظ الإعدادات." : "Settings update failed.") };
  }
  revalidatePath(`/${locale}/company`);
  return { message: locale === "ar" ? "تم حفظ إعدادات الشركة." : "Company settings saved.", success: true };
}

export async function createBranchAction(
  locale: string,
  _state: OrganizationActionState,
  formData: FormData,
): Promise<OrganizationActionState> {
  const session = await getWebSession();
  if (!session || !session.roles.some((role) => ["OWNER", "MANAGER", "HR_OFFICER"].includes(role))) {
    return { message: locale === "ar" ? "ليس لديك صلاحية." : "Permission denied." };
  }
  const parsed = branchSchema.safeParse({
    code: formData.get("code"),
    name: formData.get("name"),
    saudi_short_address: formData.get("saudi_short_address"),
    full_address: formData.get("full_address"),
    latitude: formData.get("latitude"),
    longitude: formData.get("longitude"),
    geofence_radius_m: formData.get("geofence_radius_m"),
    timezone: formData.get("timezone"),
  });
  if (!parsed.success) {
    return { message: "", errors: parsed.error.flatten().fieldErrors };
  }
  const response = await authorizedApiFetch("/branches", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...parsed.data, working_hours: {} }),
  });
  if (!response.ok) {
    const problem = await response.json().catch(() => ({})) as { detail?: string };
    return { message: problem.detail ?? (locale === "ar" ? "تعذر إنشاء الفرع." : "Branch creation failed.") };
  }
  revalidatePath(`/${locale}/company`);
  return { message: locale === "ar" ? "تم إنشاء الفرع." : "Branch created.", success: true };
}

export async function archiveBranchAction(
  locale: string,
  branchId: string,
  version: number,
): Promise<void> {
  const session = await getWebSession();
  if (!session || !session.roles.some((role) => ["OWNER", "MANAGER", "HR_OFFICER"].includes(role))) {
    return;
  }
  await authorizedApiFetch(`/branches/${branchId}?version=${version}`, { method: "DELETE" });
  revalidatePath(`/${locale}/company`);
}

export async function createShiftAction(
  locale: string,
  _state: OrganizationActionState,
  formData: FormData,
): Promise<OrganizationActionState> {
  const session = await getWebSession();
  if (!session || !session.roles.some((role) => ["OWNER", "MANAGER", "HR_OFFICER"].includes(role))) {
    return { message: locale === "ar" ? "ليس لديك صلاحية." : "Permission denied." };
  }
  const parsed = shiftSchema.safeParse({
    code: formData.get("code"),
    name: formData.get("name"),
    start_time: formData.get("start_time"),
    end_time: formData.get("end_time"),
    working_days: formData.getAll("working_days"),
    grace_period_minutes: formData.get("grace_period_minutes"),
    break_duration_minutes: formData.get("break_duration_minutes"),
    effective_from: formData.get("effective_from"),
    effective_to: formData.get("effective_to"),
  });
  if (!parsed.success) {
    return { message: "", errors: parsed.error.flatten().fieldErrors };
  }
  const response = await authorizedApiFetch("/shifts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...parsed.data, recurrence: { frequency: "weekly" } }),
  });
  if (!response.ok) {
    const problem = await response.json().catch(() => ({})) as { detail?: string };
    return { message: problem.detail ?? (locale === "ar" ? "تعذر إنشاء الوردية." : "Shift creation failed.") };
  }
  revalidatePath(`/${locale}/company`);
  return { message: locale === "ar" ? "تم إنشاء الوردية." : "Shift created.", success: true };
}

export async function archiveShiftAction(
  locale: string,
  shiftId: string,
  version: number,
): Promise<void> {
  const session = await getWebSession();
  if (!session || !session.roles.some((role) => ["OWNER", "MANAGER", "HR_OFFICER"].includes(role))) {
    return;
  }
  await authorizedApiFetch(`/shifts/${shiftId}?version=${version}`, { method: "DELETE" });
  revalidatePath(`/${locale}/company`);
}
