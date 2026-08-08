import Link from "next/link";
import { redirect } from "next/navigation";

import { authorizedApiFetch, getWebSession } from "@/lib/auth/server-session";

import {
  createCouponAction,
  createPlanAction,
  endSupportModeAction,
  startSupportModeAction,
  updatePlanAction,
  updatePlatformCompanyAction,
} from "./actions";

type Dashboard = {
  companies: number;
  active_companies: number;
  trial_companies: number;
  suspended_companies: number;
  active_subscriptions: number;
  expired_subscriptions: number;
  employees: number;
  branches: number;
};

type Company = {
  id: string;
  display_name: string;
  technical_name: string;
  status: string;
  employees: number;
  branches: number;
  plan_code: string | null;
  subscription_status: string | null;
  subscription_ends_at: string | null;
};

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
  is_active: boolean;
  version: number;
};

type Coupon = {
  id: string;
  code: string;
  discount_type: string;
  discount_value: number;
  plan_id: string | null;
  billing_cycle: string | null;
  redeemed_count: number;
  max_redemptions: number | null;
  valid_until: string;
  is_active: boolean;
};

type SupportMode = {
  id: string;
  company_name: string;
  reason: string;
  expires_at: string;
  banner: string;
};

async function jsonOr<T>(response: Response, fallback: T): Promise<T> {
  return response.ok ? ((await response.json()) as T) : fallback;
}

export default async function PlatformPortal({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  const ar = lang === "ar";
  if (!(await getWebSession())) redirect(`/${lang}/login`);
  const [dashboardResponse, companiesResponse, plansResponse, couponsResponse, supportResponse] =
    await Promise.all([
      authorizedApiFetch("/platform/dashboard"),
      authorizedApiFetch("/platform/companies"),
      authorizedApiFetch("/platform/plans"),
      authorizedApiFetch("/platform/coupons"),
      authorizedApiFetch("/platform/support-mode"),
    ]);
  if (!dashboardResponse.ok || !companiesResponse.ok) {
    return (
      <main className="foundation-shell">
        <section className="foundation-card compact">
          <div className="foundation-mark">!</div>
          <h1>{ar ? "الوصول مرفوض" : "Access denied"}</h1>
          <p className="foundation-description">
            {ar
              ? "يجب إضافة بريدك إلى PLATFORM_ADMIN_EMAILS على الخادم للوصول إلى لوحة مالك المنصة."
              : "Your email must be explicitly configured in PLATFORM_ADMIN_EMAILS to access the platform owner console."}
          </p>
          <Link className="language-link" href={`/${lang}/company`}>
            {ar ? "العودة إلى الشركة" : "Back to company"}
          </Link>
        </section>
      </main>
    );
  }

  const dashboard = await jsonOr<Dashboard>(dashboardResponse, {} as Dashboard);
  const companies = await jsonOr<Company[]>(companiesResponse, []);
  const plans = await jsonOr<Plan[]>(plansResponse, []);
  const coupons = await jsonOr<Coupon[]>(couponsResponse, []);
  const supportModes = await jsonOr<SupportMode[]>(supportResponse, []);

  return (
    <main className="portal-shell">
      <section className="portal-card wide platform-console">
        {supportModes.map((mode) => {
          const endAction = endSupportModeAction.bind(null, lang, mode.id);
          return (
            <aside className="status-banner" key={mode.id} role="status">
              <strong>{mode.banner}</strong>
              <span>{mode.reason} · {new Date(mode.expires_at).toLocaleString(lang)}</span>
              <form action={endAction}><button type="submit">{ar ? "إنهاء وضع الدعم" : "Exit support mode"}</button></form>
            </aside>
          );
        })}

        <header className="portal-header">
          <div>
            <p className="foundation-eyebrow">HADIR | حاضر · SUPER ADMIN</p>
            <h1>{ar ? "لوحة مالك المنصة" : "Platform owner console"}</h1>
            <p>{ar ? "إدارة الشركات والاشتراكات والباقات والدعم مع سجل تدقيق مستقل." : "Audited company, subscription, plan, coupon, and support controls."}</p>
          </div>
          <Link className="language-link secondary" href={`/${lang}/company`}>
            {ar ? "لوحة الشركة" : "Company portal"}
          </Link>
        </header>

        <section className="metric-grid">
          {[
            [ar ? "الشركات" : "Companies", dashboard.companies],
            [ar ? "النشطة" : "Active", dashboard.active_companies],
            [ar ? "التجريبية" : "Trials", dashboard.trial_companies],
            [ar ? "المعلقة" : "Suspended", dashboard.suspended_companies],
            [ar ? "الموظفون" : "Employees", dashboard.employees],
            [ar ? "الفروع" : "Branches", dashboard.branches],
          ].map(([label, number]) => <article className="metric-card" key={String(label)}><span>{label}</span><strong>{number}</strong></article>)}
        </section>

        <section className="portal-section">
          <h2>{ar ? "الشركات والاشتراكات" : "Companies and subscriptions"}</h2>
          <div className="platform-company-grid">
            {companies.map((company) => {
              const updateAction = updatePlatformCompanyAction.bind(null, lang, company.id);
              const supportAction = startSupportModeAction.bind(null, lang, company.id);
              return (
                <article className="operation-form-card" key={company.id}>
                  <div className="section-heading"><div><h3>{company.display_name}</h3><small>{company.technical_name} · {company.employees} users · {company.branches} branches</small></div><span className="status-pill">{company.status}</span></div>
                  <p>{company.plan_code || (ar ? "بدون باقة" : "No plan")} · {company.subscription_status || "inactive"}</p>
                  <form action={updateAction} className="portal-form">
                    <select name="company_status" defaultValue={company.status}><option value="active">Active</option><option value="trial">Trial</option><option value="suspended">Suspended</option><option value="inactive">Inactive</option></select>
                    <select name="plan_id" defaultValue=""><option value="">{ar ? "بدون تغيير الباقة" : "Keep current plan"}</option>{plans.filter((plan) => plan.is_active).map((plan) => <option key={plan.id} value={plan.id}>{plan.name}</option>)}</select>
                    <select name="billing_cycle" defaultValue="monthly"><option value="trial">Trial</option><option value="monthly">Monthly</option><option value="annual">Annual</option></select>
                    <input name="duration_days" type="number" min="1" max="3660" defaultValue="30" />
                    <input name="coupon_code" placeholder={ar ? "رمز كوبون اختياري" : "Optional coupon code"} />
                    <input name="activation_note" required minLength={3} placeholder={ar ? "سبب التعديل" : "Change reason"} />
                    <button type="submit">{ar ? "حفظ التغييرات" : "Save changes"}</button>
                  </form>
                  <details><summary>{ar ? "دخول وضع الدعم" : "Enter support mode"}</summary><form action={supportAction} className="portal-form"><input name="reason" required minLength={5} placeholder={ar ? "سبب الدعم" : "Support reason"} /><input name="duration_minutes" type="number" min="5" max="120" defaultValue="30" /><button type="submit">{ar ? "بدء وضع الدعم" : "Start support mode"}</button></form></details>
                </article>
              );
            })}
          </div>
        </section>

        <section className="portal-section split-sections">
          <div>
            <h2>{ar ? "إنشاء باقة" : "Create plan"}</h2>
            <form action={createPlanAction.bind(null, lang)} className="portal-form">
              <input name="code" required placeholder="GROWTH" />
              <input name="name" required placeholder={ar ? "اسم الباقة" : "Plan name"} />
              <textarea name="description" placeholder={ar ? "الوصف" : "Description"} />
              <input name="monthly_price" type="number" min="0" required placeholder={ar ? "السعر الشهري بأصغر وحدة" : "Monthly price in minor units"} />
              <input name="annual_price" type="number" min="0" required placeholder={ar ? "السعر السنوي بأصغر وحدة" : "Annual price in minor units"} />
              <input name="currency" defaultValue="SAR" minLength={3} maxLength={3} />
              <textarea name="limits" required defaultValue={'{"employees":50,"branches":3,"storage_mb":2048}'} />
              <textarea name="features" required defaultValue={'{"gps":true,"qr":true,"tasks":true,"documents":true,"reports":"basic"}'} />
              <input name="support_level" defaultValue="standard" />
              <button type="submit">{ar ? "إنشاء الباقة" : "Create plan"}</button>
            </form>
          </div>
          <div>
            <h2>{ar ? "الباقات الحالية" : "Current plans"}</h2>
            {plans.map((plan) => (
              <details key={plan.id} className="operation-form-card">
                <summary>{plan.name} · {plan.code} · v{plan.version}</summary>
                <form action={updatePlanAction.bind(null, lang, plan.id)} className="portal-form">
                  <input type="hidden" name="version" value={plan.version} />
                  <input name="name" defaultValue={plan.name} required />
                  <input name="monthly_price" type="number" min="0" defaultValue={plan.monthly_price} required />
                  <input name="annual_price" type="number" min="0" defaultValue={plan.annual_price} required />
                  <input name="currency" defaultValue={plan.currency} required />
                  <textarea name="limits" defaultValue={JSON.stringify(plan.limits)} required />
                  <textarea name="features" defaultValue={JSON.stringify(plan.features)} required />
                  <input name="support_level" defaultValue={plan.support_level} required />
                  <select name="is_active" defaultValue={String(plan.is_active)}><option value="true">Active</option><option value="false">Inactive</option></select>
                  <button type="submit">{ar ? "تحديث الباقة" : "Update plan"}</button>
                </form>
              </details>
            ))}
          </div>
        </section>

        <section className="portal-section split-sections">
          <div>
            <h2>{ar ? "إنشاء كوبون" : "Create coupon"}</h2>
            <form action={createCouponAction.bind(null, lang)} className="portal-form">
              <input name="code" required placeholder="WELCOME20" />
              <select name="discount_type"><option value="percent">Percent</option><option value="fixed">Fixed amount</option></select>
              <input name="discount_value" type="number" min="1" required />
              <select name="plan_id" defaultValue=""><option value="">{ar ? "كل الباقات" : "All plans"}</option>{plans.map((plan) => <option key={plan.id} value={plan.id}>{plan.name}</option>)}</select>
              <select name="billing_cycle" defaultValue=""><option value="">{ar ? "كل دورات الفوترة" : "All billing cycles"}</option><option value="monthly">Monthly</option><option value="annual">Annual</option></select>
              <input name="max_redemptions" type="number" min="1" placeholder={ar ? "الحد الأقصى" : "Maximum redemptions"} />
              <input name="valid_from" type="datetime-local" required />
              <input name="valid_until" type="datetime-local" required />
              <button type="submit">{ar ? "إنشاء" : "Create"}</button>
            </form>
          </div>
          <div>
            <h2>{ar ? "الكوبونات" : "Coupons"}</h2>
            <ul className="operation-list">{coupons.map((coupon) => <li key={coupon.id}><div><strong>{coupon.code}</strong><span>{coupon.discount_value}{coupon.discount_type === "percent" ? "%" : ""} · {coupon.redeemed_count}/{coupon.max_redemptions ?? "∞"}</span><small>{coupon.billing_cycle || "all cycles"} · {coupon.valid_until}</small></div><span className="status-pill">{coupon.is_active ? "active" : "inactive"}</span></li>)}</ul>
          </div>
        </section>
      </section>
    </main>
  );
}
