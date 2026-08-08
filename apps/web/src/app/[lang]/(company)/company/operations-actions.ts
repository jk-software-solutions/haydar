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

async function mutate(locale: string, path: string, method: string, payload: object) {
  const session = await getWebSession();
  if (!session) return;
  await authorizedApiFetch(path, {
    method,
    headers: { "Content-Type": "application/json" },
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
    completion_attachment_key: optionalText(formData, "completion_attachment_key"),
  });
}

export async function createPermissionAction(locale: string, formData: FormData): Promise<void> {
  await mutate(locale, "/permission-requests", "POST", {
    request_type: text(formData, "request_type"),
    starts_at: text(formData, "starts_at"),
    ends_at: text(formData, "ends_at"),
    reason: text(formData, "reason"),
    attachment_key: optionalText(formData, "attachment_key"),
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
    attachment_key: optionalText(formData, "attachment_key"),
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
    attachment_key: text(formData, "attachment_key"),
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

export type QrTokenState = { token?: string; expiresAt?: string; message?: string };

export async function createQrTokenAction(
  _locale: string,
  _state: QrTokenState,
  formData: FormData,
): Promise<QrTokenState> {
  if (!(await getWebSession())) return { message: "Authentication required." };
  const response = await authorizedApiFetch("/attendance/qr-tokens", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      branch_id: text(formData, "branch_id"),
      valid_for_seconds: Number(text(formData, "valid_for_seconds") || "120"),
    }),
  });
  if (!response.ok) {
    const problem = (await response.json().catch(() => ({}))) as { detail?: string };
    return { message: problem.detail ?? "QR creation failed." };
  }
  const payload = (await response.json()) as { token: string; expires_at: string };
  return { token: payload.token, expiresAt: payload.expires_at };
}

export async function createPresenceRequestAction(locale: string, formData: FormData): Promise<void> {
  await mutate(locale, "/presence-requests", "POST", {
    membership_ids: formData.getAll("membership_ids").map(String).filter(Boolean),
    message: text(formData, "message"),
    deadline_seconds: Number(text(formData, "deadline_seconds") || "300"),
  });
}

export async function createReportExportAction(locale: string, formData: FormData): Promise<void> {
  await mutate(locale, "/reports/exports", "POST", {
    report_type: text(formData, "report_type"),
    export_format: text(formData, "export_format"),
    date_from: optionalText(formData, "date_from"),
    date_to: optionalText(formData, "date_to"),
    locale,
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
