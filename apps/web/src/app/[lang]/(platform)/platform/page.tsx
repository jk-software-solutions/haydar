import Link from "next/link";
import { redirect } from "next/navigation";

import { authorizedApiFetch, getWebSession } from "@/lib/auth/server-session";

import { createCouponAction, startSupportModeAction, updatePlatformCompanyAction } from "./actions";

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
type Plan = { id: string; code: string; name: string };
type Coupon = {
  id: string;
  code: string;
  discount_type: string;
  discount_value: number;
  redeemed_count: number;
  max_redemptions: number | null;
  valid_until: string;
  is_active: boolean;
};

export default async function PlatformPortal({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  const ar = lang === "ar";
  if (!(await getWebSession())) redirect(`/${lang}/login`);
  const [dashboardResponse, companiesResponse, plansResponse, couponsResponse] = await Promise.all([
    authorizedApiFetch("/platform/dashboard"),
    authorizedApiFetch("/platform/companies"),
    authorizedApiFetch("/billing/plans"),
    authorizedApiFetch("/platform/coupons"),
  ]);
  if (!dashboardResponse.ok || !companiesResponse.ok) {
    return <main className="foundation-shell"><section className="foundation-card compact"><div className="foundation-mark">!</div><h1>{ar ? "الوصول مرفوض" : "Access denied"}</h1><p className="foundation-description">{ar ? "يجب إضافة بريدك إلى PLATFORM_ADMIN_EMAILS على الخادم للوصول إلى لوحة مالك المنصة." : "Your email must be explicitly configured in PLATFORM_ADMIN_EMAILS to access the platform owner console."}</p><Link className="language-link" href={`/${lang}/company`}>{ar ? "العودة إلى الشركة" : "Back to company"}</Link></section></main>;
  }
  const dashboard = (await dashboardResponse.json()) as Dashboard;
  const companies = (await companiesResponse.json()) as Company[];
  const plans = plansResponse.ok ? ((await plansResponse.json()) as Plan[]) : [];
  const coupons = couponsResponse.ok ? ((await couponsResponse.json()) as Coupon[]) : [];
  const couponAction = createCouponAction.bind(null, lang);

  return <main className="portal-shell"><section className="portal-card wide platform-console"><header className="portal-header"><div><p className="foundation-eyebrow">HADIR | حاضر · SUPER ADMIN</p><h1>{ar ? "لوحة مالك المنصة" : "Platform owner console"}</h1><p>{ar ? "إدارة الشركات والاشتراكات والدعم مع سجل تدقيق مستقل." : "Company, subscription, coupon, and audited support controls."}</p></div><Link className="language-link secondary" href={`/${lang}/company`}>{ar ? "لوحة الشركة" : "Company portal"}</Link></header><section className="metric-grid">{[[ar ? "الشركات" : "Companies", dashboard.companies],[ar ? "النشطة" : "Active", dashboard.active_companies],[ar ? "التجريبية" : "Trials", dashboard.trial_companies],[ar ? "المعلقة" : "Suspended", dashboard.suspended_companies],[ar ? "الموظفون" : "Employees", dashboard.employees],[ar ? "الفروع" : "Branches", dashboard.branches]].map(([label, number]) => <article className="metric-card" key={String(label)}><span>{label}</span><strong>{number}</strong></article>)}</section><section className="portal-section"><h2>{ar ? "الشركات والاشتراكات" : "Companies and subscriptions"}</h2><div className="platform-company-grid">{companies.map((company) => { const updateAction = updatePlatformCompanyAction.bind(null, lang, company.id); const supportAction = startSupportModeAction.bind(null, lang, company.id); return <article className="operation-form-card" key={company.id}><div className="section-heading"><div><h3>{company.display_name}</h3><small>{company.technical_name} · {company.employees} users · {company.branches} branches</small></div><span className="status-pill">{company.status}</span></div><p>{company.plan_code || "No plan"} · {company.subscription_status || "inactive"}</p><form action={updateAction} className="portal-form"><select name="company_status" defaultValue={company.status}><option value="active">Active</option><option value="trial">Trial</option><option value="suspended">Suspended</option><option value="inactive">Inactive</option></select><select name="plan_id" defaultValue=""><option value="">{ar ? "بدون تغيير الباقة" : "Keep current plan"}</option>{plans.map((plan) => <option key={plan.id} value={plan.id}>{plan.name}</option>)}</select><select name="billing_cycle" defaultValue="monthly"><option value="trial">Trial</option><option value="monthly">Monthly</option><option value="annual">Annual</option></select><input name="duration_days" type="number" min="1" max="3660" defaultValue="30" /><input name="activation_note" required minLength={3} placeholder={ar ? "سبب التعديل" : "Change reason"} /><button type="submit">{ar ? "حفظ التغييرات" : "Save changes"}</button></form><details><summary>{ar ? "دخول وضع الدعم" : "Enter support mode"}</summary><form action={supportAction} className="portal-form"><input name="reason" required minLength={5} placeholder={ar ? "سبب الدعم" : "Support reason"} /><input name="duration_minutes" type="number" min="5" max="120" defaultValue="30" /><button type="submit">{ar ? "بدء وضع الدعم" : "Start support mode"}</button></form></details></article>; })}</div></section><section className="portal-section split-sections"><div><h2>{ar ? "إنشاء كوبون" : "Create coupon"}</h2><form action={couponAction} className="portal-form"><input name="code" required placeholder="WELCOME20" /><select name="discount_type"><option value="percent">Percent</option><option value="fixed">Fixed amount</option></select><input name="discount_value" type="number" min="1" required /><input name="max_redemptions" type="number" min="1" placeholder={ar ? "الحد الأقصى" : "Maximum redemptions"} /><input name="valid_from" type="datetime-local" required /><input name="valid_until" type="datetime-local" required /><button type="submit">{ar ? "إنشاء" : "Create"}</button></form></div><div><h2>{ar ? "الكوبونات" : "Coupons"}</h2><ul className="operation-list">{coupons.map((coupon) => <li key={coupon.id}><div><strong>{coupon.code}</strong><span>{coupon.discount_value}{coupon.discount_type === "percent" ? "%" : ""} · {coupon.redeemed_count}/{coupon.max_redemptions ?? "∞"}</span><small>{coupon.valid_until}</small></div><span className="status-pill">{coupon.is_active ? "active" : "inactive"}</span></li>)}</ul></div></section></section></main>;
}
