"use server";

import { revalidatePath } from "next/cache";

import { authorizedApiFetch, getWebSession } from "@/lib/auth/server-session";

function value(formData: FormData, key: string): string {
  return String(formData.get(key) ?? "").trim();
}

function optionalNumber(formData: FormData, key: string): number | undefined {
  const raw = value(formData, key);
  if (!raw) return undefined;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : undefined;
}

export async function updatePlatformCompanyAction(
  locale: string,
  companyId: string,
  formData: FormData,
): Promise<void> {
  if (!(await getWebSession())) return;
  const planId = value(formData, "plan_id");
  const body = {
    company_status: value(formData, "company_status") || undefined,
    plan_id: planId || undefined,
    billing_cycle: planId ? value(formData, "billing_cycle") : undefined,
    duration_days: planId ? Number(value(formData, "duration_days")) : undefined,
    coupon_code: planId ? value(formData, "coupon_code") || undefined : undefined,
    employee_limit: planId ? optionalNumber(formData, "employee_limit") : undefined,
    branch_limit: planId ? optionalNumber(formData, "branch_limit") : undefined,
    storage_limit_mb: planId ? optionalNumber(formData, "storage_limit_mb") : undefined,
    activation_note: value(formData, "activation_note"),
  };
  await authorizedApiFetch(`/platform/companies/${companyId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", "Idempotency-Key": crypto.randomUUID() },
    body: JSON.stringify(body),
  });
  revalidatePath(`/${locale}/platform`);
}

export async function createCouponAction(locale: string, formData: FormData): Promise<void> {
  if (!(await getWebSession())) return;
  await authorizedApiFetch("/platform/coupons", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      code: value(formData, "code"),
      discount_type: value(formData, "discount_type"),
      discount_value: Number(value(formData, "discount_value")),
      plan_id: value(formData, "plan_id") || undefined,
      billing_cycle: value(formData, "billing_cycle") || undefined,
      max_redemptions: Number(value(formData, "max_redemptions")) || undefined,
      valid_from: value(formData, "valid_from"),
      valid_until: value(formData, "valid_until"),
    }),
  });
  revalidatePath(`/${locale}/platform`);
}

function numberValue(formData: FormData, key: string): number {
  const parsed = Number(value(formData, key));
  return Number.isFinite(parsed) ? parsed : 0;
}

function planLimits(formData: FormData): Record<string, number> {
  return {
    employees: numberValue(formData, "employees_limit"),
    branches: numberValue(formData, "branches_limit"),
    storage_mb: numberValue(formData, "storage_mb_limit"),
  };
}

function planFeatures(formData: FormData): Record<string, unknown> {
  return {
    gps: formData.get("feature_gps") === "on",
    qr: formData.get("feature_qr") === "on",
    wifi: formData.get("feature_wifi") === "on",
    tasks: formData.get("feature_tasks") === "on",
    documents: formData.get("feature_documents") === "on",
    reports: value(formData, "reports_level") || "basic",
  };
}

export async function createPlanAction(locale: string, formData: FormData): Promise<void> {
  if (!(await getWebSession())) return;
  await authorizedApiFetch("/platform/plans", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      code: value(formData, "code"),
      name: value(formData, "name"),
      description: value(formData, "description"),
      monthly_price: Number(value(formData, "monthly_price")),
      annual_price: Number(value(formData, "annual_price")),
      currency: value(formData, "currency") || "SAR",
      limits: planLimits(formData),
      features: planFeatures(formData),
      support_level: value(formData, "support_level") || "standard",
      is_active: value(formData, "is_active") !== "false",
    }),
  });
  revalidatePath(`/${locale}/platform`);
}

export async function updatePlanAction(
  locale: string,
  planId: string,
  formData: FormData,
): Promise<void> {
  if (!(await getWebSession())) return;
  await authorizedApiFetch(`/platform/plans/${planId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      version: Number(value(formData, "version")),
      name: value(formData, "name"),
      description: value(formData, "description"),
      monthly_price: Number(value(formData, "monthly_price")),
      annual_price: Number(value(formData, "annual_price")),
      currency: value(formData, "currency"),
      limits: planLimits(formData),
      features: planFeatures(formData),
      support_level: value(formData, "support_level"),
      is_active: value(formData, "is_active") === "true",
    }),
  });
  revalidatePath(`/${locale}/platform`);
}

export async function startSupportModeAction(
  locale: string,
  companyId: string,
  formData: FormData,
): Promise<void> {
  if (!(await getWebSession())) return;
  await authorizedApiFetch("/platform/support-mode", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      company_id: companyId,
      reason: value(formData, "reason"),
      duration_minutes: Number(value(formData, "duration_minutes") || "30"),
    }),
  });
  revalidatePath(`/${locale}/platform`);
}

export async function endSupportModeAction(
  locale: string,
  supportSessionId: string,
): Promise<void> {
  if (!(await getWebSession())) return;
  await authorizedApiFetch(`/platform/support-mode/${supportSessionId}/end`, {
    method: "POST",
  });
  revalidatePath(`/${locale}/platform`);
}

export async function reviewSubscriptionRequestAction(
  locale: string,
  requestId: string,
  formData: FormData,
): Promise<void> {
  if (!(await getWebSession())) return;
  await authorizedApiFetch(`/platform/subscription-requests/${requestId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      status: value(formData, "status"),
      review_note: value(formData, "review_note"),
    }),
  });
  revalidatePath(`/${locale}/platform`);
}
