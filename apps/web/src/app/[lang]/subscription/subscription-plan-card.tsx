"use client";

import { useActionState } from "react";

import {
  submitSubscriptionRequestAction,
  type SubscriptionActionState,
} from "./actions";
import { featureLabel, featureValue, limitLabel, planDescription, planName, supportLabel } from "./subscription-copy";

type Plan = {
  id: string;
  code: string;
  name: string;
  description: string;
  monthly_price: number;
  annual_price: number;
  currency: string;
  limits: Record<string, unknown>;
  features: Record<string, unknown>;
  support_level: string;
};

const initialState: SubscriptionActionState = { message: "" };

function price(value: number, currency: string, locale: string): string {
  return new Intl.NumberFormat(locale === "ar" ? "ar-SA" : "en-SA", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(value / 100);
}

export function SubscriptionPlanCard({ plan, locale, featured }: { plan: Plan; locale: string; featured?: boolean }) {
  const ar = locale === "ar";
  const action = submitSubscriptionRequestAction.bind(null, locale, plan.id);
  const [state, formAction, pending] = useActionState(action, initialState);
  const entries = Object.entries(plan.limits).filter(([, value]) => value !== null && value !== undefined);
  const features = [
    "gps", "qr", "wifi", "tasks", "documents", "reports",
  ].filter((key) => Boolean(plan.features[key]));
  return (
    <article className={`subscription-plan-card${featured ? " featured" : ""}`}>
      {featured && <span className="subscription-recommended">{ar ? "الأكثر اختيارًا" : "Most popular"}</span>}
      <div className="subscription-plan-topline"><span className="subscription-plan-code">{planName(plan, ar)}</span><span className="subscription-plan-support">{supportLabel(plan.support_level, ar)}</span></div>
      <h2>{planName(plan, ar)}</h2>
      <p className="subscription-plan-description">{planDescription(plan, ar) || (ar ? "كل الأدوات الأساسية لإدارة الحضور والموظفين." : "Everything you need to manage attendance and your team.")}</p>
      <div className="subscription-price-row"><strong>{price(plan.monthly_price, plan.currency, locale)}</strong><span>{ar ? "/ شهريًا" : "/ month"}</span></div>
      <p className="subscription-annual-hint">{ar ? `أو ${price(plan.annual_price, plan.currency, locale)} سنويًا` : `or ${price(plan.annual_price, plan.currency, locale)} annually`}</p>
      <div className="subscription-limit-list">
        {entries.map(([key, value]) => <span key={key}><strong>{String(value)}</strong> {limitLabel(key, ar)}</span>)}
      </div>
      <ul className="subscription-feature-list">
        {features.map((key) => <li key={key}><span aria-hidden="true">✓</span>{featureLabel(key, ar)}{featureValue(plan.features[key], ar) ? `: ${featureValue(plan.features[key], ar)}` : ""}</li>)}
      </ul>
      <form action={formAction} className="subscription-request-form">
        <label>{ar ? "الدورة" : "Billing cycle"}<select name="billing_cycle" defaultValue="monthly"><option value="monthly">{ar ? "شهري" : "Monthly"} · {price(plan.monthly_price, plan.currency, locale)}</option><option value="annual">{ar ? "سنوي" : "Annual"} · {price(plan.annual_price, plan.currency, locale)}</option></select></label>
        <label>{ar ? "كوبون الخصم (اختياري)" : "Coupon code (optional)"}<input name="coupon_code" placeholder={ar ? "أدخل الكود" : "Enter code"} /></label>
        <label>{ar ? "ملاحظة للمالك (اختياري)" : "Note for the platform owner (optional)"}<textarea name="note" rows={2} placeholder={ar ? "مثال: أحتاج 20 موظفًا وفرعًا واحدًا" : "Example: I need 20 employees and one branch"} /></label>
        <button type="submit" disabled={pending}>{pending ? (ar ? "جارٍ الإرسال..." : "Submitting...") : (ar ? "طلب هذه الباقة" : "Request this plan")}</button>
        {state.message && <p className={state.success ? "form-success" : "form-error"} aria-live="polite">{state.message}</p>}
      </form>
    </article>
  );
}
