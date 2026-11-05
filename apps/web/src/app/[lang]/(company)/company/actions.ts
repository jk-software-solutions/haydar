"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { authorizedApiFetch, getWebSession, logoutWithApi } from "@/lib/auth/server-session";
import { branchAssignmentSchema, branchSchema, wifiNetworkSchema } from "@/lib/validation/branch-schema";
import { invitationSchema } from "@/lib/validation/invitation-schema";
import { companySettingsSchema, employeeProfileSchema } from "@/lib/validation/organization-schema";
import { shiftAssignmentSchema, shiftSchema } from "@/lib/validation/shift-schema";

export type InvitationState = {
  message: string;
  success?: boolean;
  activationToken?: string;
  errors?: Record<string, string[]>;
};

export type OrganizationActionState = {
  message: string;
  success?: boolean;
  errors?: Record<string, string[]>;
};

export type EmployeeAvatarState = {
  message?: string;
  success?: boolean;
};

function wifiNetworksFromForm(formData: FormData) {
  const raw = String(formData.get("wifi_networks") ?? "");
  return raw
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [ssid, bssid] = line.split("|").map((part) => part.trim());
      return wifiNetworkSchema.safeParse({ ssid, bssid });
    })
    .filter((result): result is { success: true; data: { ssid: string; bssid: string } } => result.success)
    .map((result) => result.data);
}

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
    message: locale === "ar" ? "تم إنشاء الدعوة بنجاح. انسخ رمز التفعيل الآن." : "Invitation created successfully. Copy the one-time token now.",
    success: true,
    activationToken: created.activation_token,
  };
}

export async function resendInvitationCodeAction(
  locale: string,
  invitationId: string,
  _state: InvitationState,
  _formData: FormData,
): Promise<InvitationState> {
  const session = await getWebSession();
  if (!session || !session.roles.some((role) => ["OWNER", "MANAGER", "HR_OFFICER"].includes(role))) {
    return { message: locale === "ar" ? "ليس لديك صلاحية." : "Permission denied." };
  }
  const response = await authorizedApiFetch(`/invitations/${invitationId}/resend-code`, {
    method: "POST",
  });
  if (!response.ok) {
    const problem = await response.json().catch(() => ({})) as { detail?: string };
    return { message: problem.detail ?? (locale === "ar" ? "تعذر إنشاء كود جديد." : "Could not generate a new code.") };
  }
  const updated = await response.json() as { activation_token: string };
  revalidatePath(`/${locale}/company`);
  return {
    message: locale === "ar" ? "تم إنشاء كود جديد. انسخه الآن." : "New code generated. Copy it now.",
    success: true,
    activationToken: updated.activation_token,
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
    commercial_registration_number: formData.get("commercial_registration_number"),
    unified_number: formData.get("unified_number"),
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

export async function uploadEmployeeAvatarAction(
  locale: string,
  membershipId: string,
  _state: EmployeeAvatarState,
  formData: FormData,
): Promise<EmployeeAvatarState> {
  const session = await getWebSession();
  if (!session || !session.roles.some((role) => ["OWNER", "MANAGER", "HR_OFFICER"].includes(role))) {
    return { message: locale === "ar" ? "ليس لديك صلاحية." : "Permission denied." };
  }
  const upload = formData.get("avatar");
  if (!(upload instanceof File) || upload.size === 0) {
    return { message: locale === "ar" ? "اختر صورة أولاً." : "Select an image first." };
  }
  const body = new FormData();
  body.set("upload", upload);
  const uploadResponse = await authorizedApiFetch("/files", { method: "POST", body });
  if (!uploadResponse.ok) {
    const problem = (await uploadResponse.json().catch(() => ({}))) as { detail?: string };
    return { message: problem.detail ?? (locale === "ar" ? "تعذر رفع الصورة." : "Photo upload failed.") };
  }
  const uploaded = (await uploadResponse.json()) as { id?: string };
  if (!uploaded.id) return { message: locale === "ar" ? "تعذر حفظ الصورة." : "Photo was not saved." };
  const updateResponse = await authorizedApiFetch(`/employees/${membershipId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", "Idempotency-Key": crypto.randomUUID() },
    body: JSON.stringify({ version: Number(formData.get("version")), avatar_file_id: uploaded.id }),
  });
  if (!updateResponse.ok) {
    const problem = (await updateResponse.json().catch(() => ({}))) as { detail?: string };
    return { message: problem.detail ?? (locale === "ar" ? "تعذر ربط الصورة بالموظف." : "Could not link the photo to the employee.") };
  }
  revalidatePath(`/${locale}/company`);
  return { success: true, message: locale === "ar" ? "تم تحديث صورة الموظف." : "Employee photo updated." };
}

export async function updateEmployeeStatusAction(
  locale: string,
  membershipId: string,
  _state: OrganizationActionState,
  formData: FormData,
): Promise<OrganizationActionState> {
  const session = await getWebSession();
  if (!session?.permissions.includes("members:manage")) {
    return { message: locale === "ar" ? "ليس لديك صلاحية." : "Permission denied." };
  }
  const response = await authorizedApiFetch(`/employees/${membershipId}/status`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      version: Number(formData.get("membership_version")),
      status: String(formData.get("membership_status")),
      reason: String(formData.get("status_reason") ?? "").trim(),
    }),
  });
  if (!response.ok) {
    const problem = await response.json().catch(() => ({})) as { detail?: string };
    return { message: problem.detail ?? (locale === "ar" ? "تعذر تغيير حالة العضوية." : "Membership status update failed.") };
  }
  revalidatePath(`/${locale}/company`);
  return { message: locale === "ar" ? "تم تحديث حالة العضوية وإبطال الجلسات عند الحاجة." : "Membership status updated and sessions revoked when required.", success: true };
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
    commercial_registration_number: formData.get("commercial_registration_number"),
    unified_number: formData.get("unified_number"),
    contact_phone: formData.get("contact_phone"),
    tax_number: formData.get("tax_number"),
    default_locale: formData.get("default_locale"),
    timezone: formData.get("timezone"),
    country_code: formData.get("country_code"),
    attendance_biometric_policy: formData.get("attendance_biometric_policy"),
  });
  if (!parsed.success) {
    return { message: "", errors: parsed.error.flatten().fieldErrors };
  }
  let logoFileId: string | undefined;
  const logo = formData.get("logo");
  if (logo instanceof File && logo.size > 0) {
    if (!logo.type.startsWith("image/")) {
      return { message: locale === "ar" ? "يجب أن يكون الشعار صورة PNG أو JPG أو WebP." : "The logo must be a PNG, JPG, or WebP image." };
    }
    const body = new FormData();
    body.set("upload", logo);
    const uploadResponse = await authorizedApiFetch("/files", { method: "POST", body });
    if (!uploadResponse.ok) {
      const problem = await uploadResponse.json().catch(() => ({})) as { detail?: string };
      return { message: problem.detail ?? (locale === "ar" ? "تعذر رفع شعار الشركة." : "Company logo upload failed.") };
    }
    const uploaded = await uploadResponse.json() as { id?: string };
    if (!uploaded.id) return { message: locale === "ar" ? "تعذر حفظ شعار الشركة." : "Company logo was not saved." };
    logoFileId = uploaded.id;
  }
  const response = await authorizedApiFetch("/companies/current", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...parsed.data, ...(logoFileId ? { logo_file_id: logoFileId } : {}) }),
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
    is_active: formData.get("is_active") === "true",
  });
  if (!parsed.success) {
    return { message: "", errors: parsed.error.flatten().fieldErrors };
  }
  const response = await authorizedApiFetch("/branches", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...parsed.data, working_hours: {}, wifi_networks: wifiNetworksFromForm(formData) }),
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

function selectedVersionTargets(formData: FormData): { id: string; version: number }[] {
  return formData
    .getAll("targets")
    .map(String)
    .map((value) => {
      const [id, rawVersion] = value.split(":");
      return { id, version: Number(rawVersion) };
    })
    .filter((target) => target.id && Number.isInteger(target.version) && target.version > 0);
}

export async function bulkArchiveBranchesAction(locale: string, formData: FormData): Promise<void> {
  const session = await getWebSession();
  if (!session || !session.roles.some((role) => ["OWNER", "MANAGER", "HR_OFFICER"].includes(role))) {
    return;
  }
  const targets = selectedVersionTargets(formData);
  for (const target of targets) {
    await authorizedApiFetch(`/branches/${target.id}?version=${target.version}`, { method: "DELETE" });
  }
  if (targets.length > 0) revalidatePath(`/${locale}/company`);
}

export async function deactivateEmployeeAction(
  locale: string,
  membershipId: string,
  version: number,
): Promise<void> {
  const session = await getWebSession();
  if (!session?.permissions.includes("members:manage")) {
    return;
  }
  await authorizedApiFetch(`/employees/${membershipId}/status`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      version,
      status: "inactive",
      reason: "Deleted from admin portal",
    }),
  });
  revalidatePath(`/${locale}/company`);
}

export async function bulkDeactivateEmployeesAction(locale: string, formData: FormData): Promise<void> {
  const session = await getWebSession();
  if (!session?.permissions.includes("members:manage")) {
    return;
  }
  const targets = selectedVersionTargets(formData);
  for (const target of targets) {
    await authorizedApiFetch(`/employees/${target.id}/status`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        version: target.version,
        status: "inactive",
        reason: "Bulk deleted from admin portal",
      }),
    });
  }
  if (targets.length > 0) revalidatePath(`/${locale}/company`);
}

export async function updateBranchAction(
  locale: string,
  branchId: string,
  _state: OrganizationActionState,
  formData: FormData,
): Promise<OrganizationActionState> {
  const session = await getWebSession();
  if (!session?.permissions.includes("branches:manage")) {
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
    is_active: formData.get("is_active") === "true",
  });
  if (!parsed.success) {
    return { message: "", errors: parsed.error.flatten().fieldErrors };
  }
  const response = await authorizedApiFetch(`/branches/${branchId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ...parsed.data,
      wifi_networks: wifiNetworksFromForm(formData),
      manager_membership_id: String(formData.get("manager_membership_id") ?? "") || null,
      is_active: parsed.data.is_active,
      version: Number(formData.get("version")),
    }),
  });
  if (!response.ok) {
    const problem = await response.json().catch(() => ({})) as { detail?: string };
    return { message: problem.detail ?? (locale === "ar" ? "تعذر تحديث الفرع." : "Branch update failed.") };
  }
  revalidatePath(`/${locale}/company`);
  return { message: locale === "ar" ? "تم تحديث الفرع." : "Branch updated.", success: true };
}

export async function assignEmployeeToBranchAction(
  locale: string,
  _state: OrganizationActionState,
  formData: FormData,
): Promise<OrganizationActionState> {
  const session = await getWebSession();
  if (!session?.permissions.includes("assignments:manage")) {
    return { message: locale === "ar" ? "ليس لديك صلاحية." : "Permission denied." };
  }
  const membershipIds = formData.getAll("membership_ids").map(String).filter(Boolean);
  const fallbackMembershipId = String(formData.get("membership_id") ?? "");
  const selectedMembershipIds = membershipIds.length > 0 ? membershipIds : [fallbackMembershipId].filter(Boolean);
  if (selectedMembershipIds.length === 0) {
    return { message: locale === "ar" ? "اختر موظفاً واحداً على الأقل." : "Select at least one employee." };
  }
  let assigned = 0;
  let firstError = "";
  for (const membershipId of selectedMembershipIds) {
    const parsed = branchAssignmentSchema.safeParse({
      membership_id: membershipId,
      branch_id: formData.get("branch_id"),
      effective_from: formData.get("effective_from"),
      reason: formData.get("reason"),
    });
    if (!parsed.success) {
      return { message: "", errors: parsed.error.flatten().fieldErrors };
    }
    const response = await authorizedApiFetch("/branches/assignments", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(parsed.data),
    });
    if (response.ok) {
      assigned += 1;
    } else if (!firstError) {
      const problem = await response.json().catch(() => ({})) as { detail?: string };
      firstError = problem.detail ?? (locale === "ar" ? "تعذر تعيين بعض الموظفين للفرع." : "Some branch assignments failed.");
    }
  }
  revalidatePath(`/${locale}/company`);
  if (assigned !== selectedMembershipIds.length) {
    return {
      message: assigned > 0
        ? (locale === "ar"
            ? `تم تعيين ${assigned} من ${selectedMembershipIds.length}. ${firstError}`
            : `Assigned ${assigned} of ${selectedMembershipIds.length}. ${firstError}`)
        : firstError,
    };
  }
  return {
    message: locale === "ar"
      ? `تم تعيين ${assigned} موظف للفرع.`
      : `${assigned} employee${assigned === 1 ? "" : "s"} assigned to branch.`,
    success: true,
  };
}

export async function replaceBranchSupervisorsAction(
  locale: string,
  branchId: string,
  _state: OrganizationActionState,
  formData: FormData,
): Promise<OrganizationActionState> {
  const session = await getWebSession();
  if (!session?.permissions.includes("branches:manage")) {
    return { message: locale === "ar" ? "ليس لديك صلاحية." : "Permission denied." };
  }
  const version = Number(formData.get("version"));
  if (!Number.isInteger(version) || version < 1) {
    return { message: locale === "ar" ? "إصدار الفرع غير صالح." : "Invalid branch version." };
  }
  const response = await authorizedApiFetch(`/branches/${branchId}/supervisors`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      version,
      membership_ids: formData.getAll("membership_ids").map(String),
    }),
  });
  if (!response.ok) {
    const problem = await response.json().catch(() => ({})) as { detail?: string };
    return {
      message: problem.detail ?? (locale === "ar" ? "تعذر تحديث مشرفي الفرع." : "Branch supervisor update failed."),
    };
  }
  revalidatePath(`/${locale}/company`);
  return {
    message: locale === "ar" ? "تم تحديث مشرفي الفرع." : "Branch supervisors updated.",
    success: true,
  };
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
    second_start_time: formData.get("second_start_time"),
    second_end_time: formData.get("second_end_time"),
    location_policy: formData.get("location_policy"),
    working_days: formData.getAll("working_days"),
    grace_period_minutes: formData.get("grace_period_minutes"),
    checkout_grace_period_minutes: formData.get("checkout_grace_period_minutes"),
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
    body: JSON.stringify({
      code: parsed.data.code,
      name: parsed.data.name,
      start_time: parsed.data.start_time,
      end_time: parsed.data.end_time,
      working_days: parsed.data.working_days,
      grace_period_minutes: parsed.data.grace_period_minutes,
      break_duration_minutes: parsed.data.break_duration_minutes,
      effective_from: parsed.data.effective_from,
      effective_to: parsed.data.effective_to,
      recurrence: {
        frequency: "weekly",
        location_policy: parsed.data.location_policy,
        checkout_grace_period_minutes: parsed.data.checkout_grace_period_minutes,
        periods: [
          { start_time: parsed.data.start_time, end_time: parsed.data.end_time },
          ...(parsed.data.second_start_time && parsed.data.second_end_time
            ? [{ start_time: parsed.data.second_start_time, end_time: parsed.data.second_end_time }]
            : []),
        ],
      },
    }),
  });
  if (!response.ok) {
    const problem = await response.json().catch(() => ({})) as { detail?: string };
    return { message: problem.detail ?? (locale === "ar" ? "تعذر إنشاء الوردية." : "Shift creation failed.") };
  }
  revalidatePath(`/${locale}/company`);
  return { message: locale === "ar" ? "تم إنشاء الوردية." : "Shift created.", success: true };
}

export async function updateShiftAction(
  locale: string,
  shiftId: string,
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
    second_start_time: formData.get("second_start_time"),
    second_end_time: formData.get("second_end_time"),
    location_policy: formData.get("location_policy"),
    working_days: formData.getAll("working_days"),
    grace_period_minutes: formData.get("grace_period_minutes"),
    checkout_grace_period_minutes: formData.get("checkout_grace_period_minutes"),
    break_duration_minutes: formData.get("break_duration_minutes"),
    effective_from: formData.get("effective_from"),
    effective_to: formData.get("effective_to"),
  });
  if (!parsed.success) {
    return { message: "", errors: parsed.error.flatten().fieldErrors };
  }
  const response = await authorizedApiFetch(`/shifts/${shiftId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      version: Number(formData.get("version")),
      code: parsed.data.code,
      name: parsed.data.name,
      start_time: parsed.data.start_time,
      end_time: parsed.data.end_time,
      working_days: parsed.data.working_days,
      grace_period_minutes: parsed.data.grace_period_minutes,
      break_duration_minutes: parsed.data.break_duration_minutes,
      effective_from: parsed.data.effective_from,
      effective_to: parsed.data.effective_to,
      is_active: formData.get("is_active") === "true",
      recurrence: {
        frequency: "weekly",
        location_policy: parsed.data.location_policy,
        checkout_grace_period_minutes: parsed.data.checkout_grace_period_minutes,
        periods: [
          { start_time: parsed.data.start_time, end_time: parsed.data.end_time },
          ...(parsed.data.second_start_time && parsed.data.second_end_time
            ? [{ start_time: parsed.data.second_start_time, end_time: parsed.data.second_end_time }]
            : []),
        ],
      },
    }),
  });
  if (!response.ok) {
    const problem = await response.json().catch(() => ({})) as { detail?: string };
    return { message: problem.detail ?? (locale === "ar" ? "تعذر تحديث الوردية." : "Shift update failed.") };
  }
  revalidatePath(`/${locale}/company`);
  return { message: locale === "ar" ? "تم تحديث الوردية." : "Shift updated.", success: true };
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

export async function bulkArchiveShiftsAction(locale: string, formData: FormData): Promise<void> {
  const session = await getWebSession();
  if (!session || !session.roles.some((role) => ["OWNER", "MANAGER", "HR_OFFICER"].includes(role))) {
    return;
  }
  const targets = selectedVersionTargets(formData);
  for (const target of targets) {
    await authorizedApiFetch(`/shifts/${target.id}?version=${target.version}`, { method: "DELETE" });
  }
  if (targets.length > 0) revalidatePath(`/${locale}/company`);
}

export async function assignShiftAction(
  locale: string,
  _state: OrganizationActionState,
  formData: FormData,
): Promise<OrganizationActionState> {
  const session = await getWebSession();
  if (!session || !session.roles.some((role) => ["OWNER", "MANAGER", "HR_OFFICER"].includes(role))) {
    return { message: locale === "ar" ? "ليس لديك صلاحية." : "Permission denied." };
  }
  const targetType = String(formData.get("target_type") ?? "branch");
  const parsed = shiftAssignmentSchema.safeParse({
    shift_id: formData.get("shift_id"),
    target_type: targetType,
    membership_id: targetType === "employee" ? formData.get("membership_id") : "",
    branch_id: targetType === "branch" ? formData.get("branch_id") : "",
    effective_from: formData.get("effective_from"),
    effective_to: formData.get("effective_to"),
  });
  if (!parsed.success) {
    return { message: "", errors: parsed.error.flatten().fieldErrors };
  }
  const payload = {
    shift_id: parsed.data.shift_id,
    membership_id: parsed.data.target_type === "employee" ? parsed.data.membership_id : null,
    branch_id: parsed.data.target_type === "branch" ? parsed.data.branch_id : null,
    effective_from: parsed.data.effective_from,
    effective_to: parsed.data.effective_to,
  };
  const response = await authorizedApiFetch("/shifts/assignments", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const problem = await response.json().catch(() => ({})) as { detail?: string };
    return {
      message: problem.detail ?? (locale === "ar" ? "تعذر تعيين الوردية." : "Shift assignment failed."),
    };
  }
  revalidatePath(`/${locale}/company`);
  return {
    message: locale === "ar" ? "تم تعيين الوردية." : "Shift assigned.",
    success: true,
  };
}
