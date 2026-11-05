"use server";

import { revalidatePath } from "next/cache";

import { authorizedApiFetch, getWebSession } from "@/lib/auth/server-session";

function text(formData: FormData, key: string): string {
  return String(formData.get(key) ?? "").trim();
}

function optionalText(formData: FormData, key: string): string | undefined {
  const value = text(formData, key);
  return value || undefined;
}

export type FileUploadState = {
  fileId?: string;
  filename?: string;
  message?: string;
};

export async function uploadFileAction(
  _state: FileUploadState,
  formData: FormData,
): Promise<FileUploadState> {
  if (!(await getWebSession())) return { message: "Authentication required." };
  const upload = formData.get("upload");
  if (!(upload instanceof File) || upload.size === 0) {
    return { message: "Select a file first." };
  }
  const body = new FormData();
  body.set("upload", upload);
  const response = await authorizedApiFetch("/files", { method: "POST", body });
  if (!response.ok) {
    const problem = (await response.json().catch(() => ({}))) as { detail?: string };
    return { message: problem.detail ?? "Upload failed." };
  }
  const payload = (await response.json()) as { id: string; filename: string };
  return { fileId: payload.id, filename: payload.filename };
}

async function mutate(locale: string, path: string, method: string, payload: object) {
  const session = await getWebSession();
  if (!session) return;
  await authorizedApiFetch(path, {
    method,
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": crypto.randomUUID(),
    },
    body: JSON.stringify(payload),
  });
  revalidatePath(`/${locale}/company`);
}

export async function createTaskAction(locale: string, formData: FormData): Promise<void> {
  await mutate(locale, "/tasks", "POST", {
    title: text(formData, "title"),
    description: text(formData, "description"),
    priority: text(formData, "priority") || "normal",
    due_at: optionalText(formData, "due_at"),
    membership_ids: formData.getAll("membership_ids").map(String).filter(Boolean),
  });
}

export async function updateTaskStatusAction(
  locale: string,
  taskId: string,
  version: number,
  formData: FormData,
): Promise<void> {
  await mutate(locale, `/tasks/${taskId}/status`, "POST", {
    version,
    status: text(formData, "status"),
    reason: optionalText(formData, "reason"),
    requested_due_at: optionalText(formData, "requested_due_at"),
    completion_attachment_file_id: optionalText(formData, "completion_attachment_file_id"),
  });
}

export async function decideTaskExtensionAction(
  locale: string,
  taskId: string,
  version: number,
  decision: "approved" | "rejected",
  formData: FormData,
): Promise<void> {
  await mutate(locale, `/tasks/${taskId}/extension-decision`, "POST", {
    version,
    decision,
    new_due_at: decision === "approved" ? optionalText(formData, "new_due_at") : undefined,
    comment: text(formData, "comment"),
  });
}

export async function createPermissionAction(locale: string, formData: FormData): Promise<void> {
  await mutate(locale, "/permission-requests", "POST", {
    request_type: text(formData, "request_type"),
    starts_at: text(formData, "starts_at"),
    ends_at: optionalText(formData, "ends_at"),
    reason: text(formData, "reason"),
    attachment_file_id: optionalText(formData, "attachment_file_id"),
  });
}

export async function reviewPermissionAction(
  locale: string,
  requestId: string,
  decision: "approved" | "rejected",
): Promise<void> {
  await mutate(locale, `/permission-requests/${requestId}/review`, "POST", { decision });
}

export async function createLeaveTypeAction(locale: string, formData: FormData): Promise<void> {
  await mutate(locale, "/leave/types", "POST", {
    code: text(formData, "code"),
    name: text(formData, "name"),
    default_days: Number(text(formData, "default_days")),
    is_paid: formData.get("is_paid") === "on",
  });
}

export async function setLeaveBalanceAction(locale: string, formData: FormData): Promise<void> {
  await mutate(locale, "/leave/balances", "PUT", {
    membership_id: text(formData, "membership_id"),
    leave_type_id: text(formData, "leave_type_id"),
    year: Number(text(formData, "year")),
    allocated_days: Number(text(formData, "allocated_days")),
    reason: text(formData, "reason"),
  });
}

export async function createLeaveRequestAction(locale: string, formData: FormData): Promise<void> {
  await mutate(locale, "/leave/requests", "POST", {
    leave_type_id: text(formData, "leave_type_id"),
    starts_on: text(formData, "starts_on"),
    ends_on: text(formData, "ends_on"),
    reason: text(formData, "reason"),
    attachment_file_id: optionalText(formData, "attachment_file_id"),
  });
}

export async function reviewLeaveAction(
  locale: string,
  requestId: string,
  decision: "approved" | "rejected",
): Promise<void> {
  await mutate(locale, `/leave/requests/${requestId}/review`, "POST", { decision });
}

export async function createDocumentAction(locale: string, formData: FormData): Promise<void> {
  await mutate(locale, "/documents", "POST", {
    membership_id: optionalText(formData, "membership_id"),
    document_type: text(formData, "document_type"),
    custom_type_name: optionalText(formData, "custom_type_name"),
    document_number: optionalText(formData, "document_number"),
    issued_on: optionalText(formData, "issued_on"),
    expires_on: optionalText(formData, "expires_on"),
    attachment_file_id: text(formData, "attachment_file_id"),
    reminder_days: Number(text(formData, "reminder_days") || "30"),
  });
}

export async function reviewDocumentAction(
  locale: string,
  documentId: string,
  decision: "valid" | "rejected",
): Promise<void> {
  await mutate(locale, `/documents/${documentId}/review`, "POST", { decision });
}

export async function updateDocumentAction(
  locale: string,
  documentId: string,
  formData: FormData,
): Promise<void> {
  await mutate(locale, `/documents/${documentId}`, "PATCH", {
    version: Number(text(formData, "version")),
    document_type: text(formData, "document_type"),
    custom_type_name: optionalText(formData, "custom_type_name"),
    document_number: optionalText(formData, "document_number"),
    issued_on: optionalText(formData, "issued_on"),
    expires_on: optionalText(formData, "expires_on"),
    attachment_file_id: text(formData, "attachment_file_id"),
    reminder_days: Number(text(formData, "reminder_days") || "30"),
  });
}

export async function deleteDocumentAction(
  locale: string,
  documentId: string,
  version: number,
): Promise<void> {
  const session = await getWebSession();
  if (!session) return;
  await authorizedApiFetch(`/documents/${documentId}?version=${version}`, { method: "DELETE" });
  revalidatePath(`/${locale}/company`);
}

export async function createManualAttendanceAction(
  locale: string,
  formData: FormData,
): Promise<void> {
  await mutate(locale, "/attendance/manual", "POST", {
    membership_id: text(formData, "membership_id"),
    branch_id: text(formData, "branch_id"),
    shift_id: text(formData, "shift_id"),
    work_date: text(formData, "work_date"),
    checked_in_at: text(formData, "checked_in_at"),
    checked_out_at: optionalText(formData, "checked_out_at"),
    reason: text(formData, "reason"),
  });
}

export type QrTokenState = { tokenId?: string; token?: string; expiresAt?: string; message?: string };

export async function createQrTokenAction(
  _locale: string,
  _state: QrTokenState,
  formData: FormData,
): Promise<QrTokenState> {
  if (!(await getWebSession())) return { message: "Authentication required." };
  const response = await authorizedApiFetch(
    formData.get("rotate") === "true"
      ? "/attendance/qr-tokens/rotate"
      : "/attendance/qr-tokens",
    {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      branch_id: text(formData, "branch_id"),
      valid_for_seconds: Number(text(formData, "valid_for_seconds") || "120"),
    }),
    },
  );
  if (!response.ok) {
    const problem = (await response.json().catch(() => ({}))) as { detail?: string };
    return { message: problem.detail ?? "QR creation failed." };
  }
  const payload = (await response.json()) as { id: string; token: string; expires_at: string };
  return { tokenId: payload.id, token: payload.token, expiresAt: payload.expires_at };
}

export async function revokeQrTokenAction(locale: string, tokenId: string): Promise<void> {
  if (!(await getWebSession())) return;
  await authorizedApiFetch(`/attendance/qr-tokens/${tokenId}`, { method: "DELETE" });
  revalidatePath(`/${locale}/company`);
}

export async function createPresenceRequestAction(locale: string, formData: FormData): Promise<void> {
  await mutate(locale, "/presence-requests", "POST", {
    membership_ids: formData.getAll("membership_ids").map(String).filter(Boolean),
    branch_id: optionalText(formData, "branch_id"),
    group_id: optionalText(formData, "group_id"),
    message: text(formData, "message"),
    deadline_seconds: Number(text(formData, "deadline_seconds") || "300"),
  });
}

export async function createReportExportAction(locale: string, formData: FormData): Promise<void> {
  await mutate(locale, "/reports/exports", "POST", {
    report_type: text(formData, "report_type"),
    report_types: formData.getAll("report_types").map(String).filter(Boolean),
    export_format: text(formData, "export_format"),
    date_from: optionalText(formData, "date_from"),
    date_to: optionalText(formData, "date_to"),
    membership_id: optionalText(formData, "membership_id"),
    branch_id: optionalText(formData, "branch_id"),
    department_id: optionalText(formData, "department_id"),
    group_id: optionalText(formData, "group_id"),
    shift_id: optionalText(formData, "shift_id"),
    status: optionalText(formData, "status"),
    locale,
  });
}

export async function updateLeaderboardSettingsAction(
  locale: string,
  formData: FormData,
): Promise<void> {
  await mutate(locale, "/reports/leaderboard/settings", "PUT", {
    visibility: text(formData, "visibility"),
    enabled: formData.get("enabled") === "on",
    anonymize: formData.get("anonymize") === "on",
  });
}

export async function reviewGeofenceExitAction(
  locale: string,
  eventId: string,
  version: number,
  decision: "confirmed_unauthorized" | "dismissed" | "approved_exception",
  formData: FormData,
): Promise<void> {
  await mutate(locale, `/geofence-exit-events/${eventId}/review`, "POST", {
    decision,
    version,
    comment: text(formData, "comment"),
  });
}

export async function updateNotificationPreferencesAction(
  locale: string,
  formData: FormData,
): Promise<void> {
  await mutate(locale, "/notifications/preferences", "PUT", {
    in_app_enabled: formData.get("in_app_enabled") === "on",
    push_enabled: formData.get("push_enabled") === "on",
    email_enabled: formData.get("email_enabled") === "on",
    muted_kinds: text(formData, "muted_kinds").split(",").map((value) => value.trim()).filter(Boolean),
    quiet_hours_start: optionalText(formData, "quiet_hours_start"),
    quiet_hours_end: optionalText(formData, "quiet_hours_end"),
  });
}

export async function markAllNotificationsReadAction(locale: string): Promise<void> {
  await mutate(locale, "/notifications/read-all", "POST", {});
}
