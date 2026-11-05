"use server";

import { revalidatePath } from "next/cache";

import { authorizedApiFetch, getWebSession } from "@/lib/auth/server-session";

export type SubscriptionActionState = {
  message: string;
  success?: boolean;
};

export async function submitSubscriptionRequestAction(
  locale: string,
  planId: string,
  _state: SubscriptionActionState,
  formData: FormData,
): Promise<SubscriptionActionState> {
  if (!(await getWebSession())) {
    return { message: locale === "ar" ? "انتهت جلسة الدخول." : "Your session has expired." };
  }
  const billingCycle = String(formData.get("billing_cycle") ?? "monthly");
  const couponCode = String(formData.get("coupon_code") ?? "").trim();
  const note = String(formData.get("note") ?? "").trim();
  if (!(["monthly", "annual"] as string[]).includes(billingCycle)) {
    return { message: locale === "ar" ? "اختر دورة اشتراك صحيحة." : "Choose a valid billing cycle." };
  }
  const response = await authorizedApiFetch("/billing/subscription-requests", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      plan_id: planId,
      billing_cycle: billingCycle,
      coupon_code: couponCode || undefined,
      note: note || undefined,
    }),
  });
  if (!response.ok) {
    const problem = await response.json().catch(() => ({})) as { detail?: string };
    return {
      message: problem.detail ?? (locale === "ar" ? "تعذر إرسال طلب الاشتراك." : "Could not submit the subscription request."),
    };
  }
  revalidatePath(`/${locale}/subscription`);
  revalidatePath(`/${locale}/company`);
  return {
    message: locale === "ar"
      ? "تم إرسال طلبك. سيظهر الاشتراك بعد اعتماد مالك المنصة."
      : "Your request was submitted. The subscription will appear after platform approval.",
    success: true,
  };
}
