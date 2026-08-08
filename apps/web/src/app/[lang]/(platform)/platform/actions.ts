"use server";

import { revalidatePath } from "next/cache";

import { authorizedApiFetch, getWebSession } from "@/lib/auth/server-session";

function value(formData: FormData, key: string): string {
  return String(formData.get(key) ?? "").trim();
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
    activation_note: value(formData, "activation_note"),
  };
  await authorizedApiFetch(`/platform/companies/${companyId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
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
      max_redemptions: Number(value(formData, "max_redemptions")) || undefined,
      valid_from: value(formData, "valid_from"),
      valid_until: value(formData, "valid_until"),
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
