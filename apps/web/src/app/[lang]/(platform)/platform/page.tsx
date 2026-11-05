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
  reviewSubscriptionRequestAction,
} from "./actions";
import { planName, supportLabel } from "../../subscription/subscription-copy";
import { WhatsAppContact } from "@/components/whatsapp-contact";

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
  subscription_limits_override: Record<string, number> | null;
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

type SubscriptionRequest = {
  id: string;
  company_id: string;
  company_name: string;
  plan: { name: string; code: string } | null;
  billing_cycle: string;
  status: string;
  coupon_code: string | null;
  note: string | null;
  created_at: string;
};

async function jsonOr<T>(response: Response, fallback: T): Promise<T> {
  return response.ok ? ((await response.json()) as T) : fallback;
}

function companyStatusLabel(value: string, ar: boolean): string {
  return ({
    active: ar ? "نشطة" : "Active",
    trial: ar ? "تجريبية" : "Trial",
    suspended: ar ? "موقوفة" : "Suspended",
    inactive: ar ? "غير نشطة" : "Inactive",
  }[value] ?? value);
}

function billingCycleLabel(value: string, ar: boolean): string {
  return ({
    trial: ar ? "تجريبية" : "Trial",
    monthly: ar ? "شهري" : "Monthly",
    annual: ar ? "سنوي" : "Annual",
  }[value] ?? value);
}

function couponTypeLabel(value: string, ar: boolean): string {
  return value === "percent" ? (ar ? "نسبة مئوية" : "Percentage") : (ar ? "مبلغ ثابت" : "Fixed amount");
}

export default async function PlatformPortal({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  const ar = lang === "ar";
  if (!(await getWebSession())) redirect(`/${lang}/login`);
  const [dashboardResponse, companiesResponse, plansResponse, couponsResponse, supportResponse, requestsResponse] =
    await Promise.all([
      authorizedApiFetch("/platform/dashboard"),
      authorizedApiFetch("/platform/companies"),
      authorizedApiFetch("/platform/plans"),
      authorizedApiFetch("/platform/coupons"),
      authorizedApiFetch("/platform/support-mode"),
      authorizedApiFetch("/platform/subscription-requests"),
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
  const subscriptionRequests = await jsonOr<SubscriptionRequest[]>(requestsResponse, []);

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
            <p className="foundation-eyebrow">HADIR | حاضر · {ar ? "المشرف العام" : "SUPER ADMIN"}</p>
            <h1>{ar ? "لوحة مالك المنصة" : "Platform owner console"}</h1>
            <p>{ar ? "إدارة الشركات والاشتراكات والباقات والدعم مع سجل تدقيق مستقل." : "Audited company, subscription, plan, coupon, and support controls."}</p>
          </div>
          <WhatsAppContact lang={lang} />
          <Link className="language-link secondary" href={`/${lang}/company`}>
            {ar ? "لوحة الشركة" : "Company portal"}
          </Link>
          <Link className="language-link" href={`/${lang}/subscription`}>
            {ar ? "صفحة الاشتراكات" : "Subscription page"}
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
              const companyPlan = plans.find((plan) => plan.code === company.plan_code);
              return (
                <article className="operation-form-card" key={company.id}>
                  <div className="section-heading"><div><h3>{company.display_name}</h3><small>{company.technical_name} · {company.employees} {ar ? "موظف" : "users"} · {company.branches} {ar ? "فرع" : "branches"}</small></div><span className="status-pill">{companyStatusLabel(company.status, ar)}</span></div>
                  <p>{companyPlan ? planName(companyPlan, ar) : (ar ? "بدون باقة" : "No plan")} · {companyStatusLabel(company.subscription_status || "inactive", ar)}</p>
                  <p className="form-hint">{ar ? "اترك حدود الباقة فارغة لاستخدام أرقام الباقة. املأها فقط إذا كان هذا العميل يحتاج حداً خاصاً." : "Leave custom limits empty to use the plan limits. Fill them only when this customer needs a custom allowance."}</p>
                  <form action={updateAction} className="portal-form">
                    <label>{ar ? "حالة الشركة" : "Company status"}<select name="company_status" defaultValue={company.status}><option value="active">{ar ? "نشطة" : "Active"}</option><option value="trial">{ar ? "تجريبية" : "Trial"}</option><option value="suspended">{ar ? "موقوفة" : "Suspended"}</option><option value="inactive">{ar ? "غير نشطة" : "Inactive"}</option></select></label>
                    <label>{ar ? "الباقة الجديدة (اختياري)" : "New plan (optional)"}<select name="plan_id" defaultValue=""><option value="">{ar ? "بدون تغيير الباقة" : "Keep current plan"}</option>{plans.filter((plan) => plan.is_active).map((plan) => <option key={plan.id} value={plan.id}>{planName(plan, ar)}</option>)}</select></label>
                    <label>{ar ? "دورة الاشتراك" : "Billing cycle"}<select name="billing_cycle" defaultValue="monthly"><option value="trial">{billingCycleLabel("trial", ar)}</option><option value="monthly">{billingCycleLabel("monthly", ar)}</option><option value="annual">{billingCycleLabel("annual", ar)}</option></select></label>
                    <label>{ar ? "المدة بالأيام" : "Duration in days"}<input name="duration_days" type="number" min="1" max="3660" defaultValue="30" /></label>
                    <label>{ar ? "عدد الموظفين المخصص" : "Custom employee limit"}<input name="employee_limit" type="number" min="1" max="1000000" defaultValue={company.subscription_limits_override?.employees ?? ""} placeholder={ar ? "حد الباقة" : "Plan limit"} /></label>
                    <label>{ar ? "عدد الفروع المخصص" : "Custom branch limit"}<input name="branch_limit" type="number" min="1" max="1000000" defaultValue={company.subscription_limits_override?.branches ?? ""} placeholder={ar ? "حد الباقة" : "Plan limit"} /></label>
                    <label>{ar ? "التخزين المخصص (ميجابايت)" : "Custom storage (MB)"}<input name="storage_limit_mb" type="number" min="1" max="1000000" defaultValue={company.subscription_limits_override?.storage_mb ?? ""} placeholder={ar ? "حد الباقة" : "Plan limit"} /></label>
                    <input name="coupon_code" placeholder={ar ? "رمز كوبون اختياري" : "Optional coupon code"} />
                    <input name="activation_note" required minLength={3} placeholder={ar ? "سبب التعديل" : "Change reason"} />
                    <button type="submit">{ar ? "تفعيل / حفظ الاشتراك" : "Activate / save subscription"}</button>
                  </form>
                  <details><summary>{ar ? "دخول وضع الدعم" : "Enter support mode"}</summary><form action={supportAction} className="portal-form"><input name="reason" required minLength={5} placeholder={ar ? "سبب الدعم" : "Support reason"} /><input name="duration_minutes" type="number" min="5" max="120" defaultValue="30" /><button type="submit">{ar ? "بدء وضع الدعم" : "Start support mode"}</button></form></details>
                </article>
              );
            })}
          </div>
        </section>

        <section className="portal-section">
          <div className="section-heading">
            <div>
              <h2>{ar ? "طلبات شراء الاشتراكات" : "Subscription purchase requests"}</h2>
              <p className="form-hint">{ar ? "كل طلب يرسله مالك الشركة يظهر هنا. راجع الباقة والكوبون ثم اعتمد الطلب أو ارفضه." : "Every company purchase request appears here. Review the plan and coupon, then approve or reject it."}</p>
            </div>
            <span className="status-pill">{subscriptionRequests.length} {ar ? "قيد المراجعة" : "pending"}</span>
          </div>
          {subscriptionRequests.length === 0 ? (
            <p className="empty-state">{ar ? "لا توجد طلبات معلقة." : "There are no pending requests."}</p>
          ) : (
            <div className="subscription-request-list">
              {subscriptionRequests.map((request) => (
                <article className="subscription-request-history" key={request.id}>
                  <div><strong>{request.company_name}</strong><span>{request.plan ? planName(request.plan, ar) : (ar ? "باقة غير معروفة" : "Unknown plan")} · {billingCycleLabel(request.billing_cycle, ar)}</span><small>{request.coupon_code ? `${ar ? "الكوبون" : "Coupon"}: ${request.coupon_code} · ` : ""}{request.note || (ar ? "بدون ملاحظة" : "No note")}</small></div>
                  <form action={reviewSubscriptionRequestAction.bind(null, lang, request.id)} className="portal-form inline">
                    <select name="status" defaultValue="approved"><option value="approved">{ar ? "اعتماد وتفعيل" : "Approve and activate"}</option><option value="rejected">{ar ? "رفض" : "Reject"}</option></select>
                    <input name="review_note" required minLength={3} placeholder={ar ? "ملاحظة المراجعة" : "Review note"} />
                    <button type="submit">{ar ? "حفظ القرار" : "Save decision"}</button>
                  </form>
                </article>
              ))}
            </div>
          )}
        </section>

        <section className="portal-section plan-management-section">
          <div className="plan-management-grid">
          <div className="plan-panel plan-create-panel">
            <h2>{ar ? "إضافة باقة اشتراك" : "Add a subscription plan"}</h2>
            <p className="form-hint">{ar ? "املأ بيانات الباقة واحفظها. اختر «غير نشطة» إذا كنت تريد إعدادها الآن وإخفاءها عن العملاء مؤقتًا." : "Complete the plan details and save. Choose Inactive to prepare a plan now while hiding it from customers temporarily."}</p>
            <form action={createPlanAction.bind(null, lang)} className="portal-form plan-form">
              <div className="plan-form-grid">
                <label>{ar ? "رمز الباقة" : "Plan code"}<input name="code" required maxLength={40} placeholder="GROWTH" /></label>
                <label>{ar ? "اسم الباقة" : "Plan name"}<input name="name" required maxLength={120} placeholder={ar ? "مثال: الباقة الاحترافية" : "Example: Professional"} /></label>
                <label className="plan-field-wide">{ar ? "وصف الباقة" : "Plan description"}<textarea name="description" maxLength={1000} placeholder={ar ? "ما الذي يحصل عليه العميل؟" : "What does the customer get?"} /></label>
                <label>{ar ? "السعر الشهري (بالهللات)" : "Monthly price (minor units)"}<input name="monthly_price" type="number" min="0" max="100000000" required placeholder="19900 = 199 SAR" /></label>
                <label>{ar ? "السعر السنوي (بالهللات)" : "Annual price (minor units)"}<input name="annual_price" type="number" min="0" max="100000000" required placeholder="199000 = 1,990 SAR" /></label>
                <label>{ar ? "العملة" : "Currency"}<input name="currency" defaultValue="SAR" minLength={3} maxLength={3} /></label>
                <label>{ar ? "حالة الباقة" : "Plan status"}<select name="is_active" defaultValue="true"><option value="true">{ar ? "نشطة — تظهر للعملاء" : "Active — visible to customers"}</option><option value="false">{ar ? "غير نشطة — محفوظة ومخفية" : "Inactive — saved but hidden"}</option></select></label>
              </div>
              <fieldset className="plan-form-section"><legend>{ar ? "حدود الباقة" : "Plan limits"}</legend><div className="plan-form-grid"><label>{ar ? "الموظفون" : "Employees"}<input name="employees_limit" type="number" min="1" max="1000000" required defaultValue="50" /></label><label>{ar ? "الفروع" : "Branches"}<input name="branches_limit" type="number" min="1" max="1000000" required defaultValue="3" /></label><label>{ar ? "التخزين (ميجابايت)" : "Storage (MB)"}<input name="storage_mb_limit" type="number" min="1" max="100000000" required defaultValue="2048" /></label></div></fieldset>
              <fieldset className="plan-form-section"><legend>{ar ? "مزايا الباقة" : "Plan features"}</legend><div className="plan-feature-grid"><label className="checkbox-field"><input type="checkbox" name="feature_gps" defaultChecked />{ar ? "الحضور عبر نظام تحديد المواقع" : "GPS attendance"}</label><label className="checkbox-field"><input type="checkbox" name="feature_qr" defaultChecked />{ar ? "رمز الاستجابة السريعة" : "QR code"}</label><label className="checkbox-field"><input type="checkbox" name="feature_wifi" defaultChecked />{ar ? "الحضور عبر الشبكة اللاسلكية" : "Wi‑Fi attendance"}</label><label className="checkbox-field"><input type="checkbox" name="feature_tasks" defaultChecked />{ar ? "المهام" : "Tasks"}</label><label className="checkbox-field"><input type="checkbox" name="feature_documents" defaultChecked />{ar ? "الوثائق والمرفقات" : "Documents and attachments"}</label></div><label>{ar ? "مستوى التقارير" : "Reports level"}<select name="reports_level" defaultValue="basic"><option value="basic">{ar ? "أساسية" : "Basic"}</option><option value="advanced">{ar ? "متقدمة" : "Advanced"}</option></select></label></fieldset>
              <label>{ar ? "مستوى الدعم" : "Support level"}<select name="support_level" defaultValue="standard"><option value="community">{supportLabel("community", ar)}</option><option value="standard">{supportLabel("standard", ar)}</option><option value="priority">{supportLabel("priority", ar)}</option><option value="dedicated">{supportLabel("dedicated", ar)}</option></select></label>
              <button type="submit">{ar ? "إنشاء الباقة" : "Create plan"}</button>
            </form>
          </div>
          <div className="plan-panel plan-current-panel">
            <h2>{ar ? "الباقات الحالية" : "Current plans"}</h2>
            <p className="form-hint">{ar ? "التعديل يحفظ السعر والحدود والمزايا والحالة. الباقة غير النشطة تبقى محفوظة ولا تظهر في صفحة شراء العميل." : "Updates save the price, limits, features, and status. Inactive plans remain saved but are hidden from the customer purchase page."}</p>
            <div className="plan-current-list">{plans.map((plan) => (
              <details key={plan.id} className="operation-form-card plan-current-card">
                <summary>{planName(plan, ar)} · {ar ? "الرمز" : "Code"}: {plan.code} · {ar ? "الإصدار" : "Version"} {plan.version} <span className="status-pill">{plan.is_active ? (ar ? "نشطة" : "Active") : (ar ? "غير نشطة" : "Inactive")}</span></summary>
                <form action={updatePlanAction.bind(null, lang, plan.id)} className="portal-form plan-form">
                  <input type="hidden" name="version" value={plan.version} />
                  <div className="plan-form-grid"><label>{ar ? "اسم الباقة" : "Plan name"}<input name="name" defaultValue={plan.name} required maxLength={120} /></label><label>{ar ? "العملة" : "Currency"}<input name="currency" defaultValue={plan.currency} minLength={3} maxLength={3} required /></label><label className="plan-field-wide">{ar ? "وصف الباقة" : "Plan description"}<textarea name="description" defaultValue={plan.description} maxLength={1000} /></label><label>{ar ? "السعر الشهري (بالهللات)" : "Monthly price (minor units)"}<input name="monthly_price" type="number" min="0" max="100000000" defaultValue={plan.monthly_price} required /></label><label>{ar ? "السعر السنوي (بالهللات)" : "Annual price (minor units)"}<input name="annual_price" type="number" min="0" max="100000000" defaultValue={plan.annual_price} required /></label></div>
                  <fieldset className="plan-form-section"><legend>{ar ? "حدود الباقة" : "Plan limits"}</legend><div className="plan-form-grid"><label>{ar ? "الموظفون" : "Employees"}<input name="employees_limit" type="number" min="1" max="1000000" required defaultValue={Number(plan.limits.employees ?? 1)} /></label><label>{ar ? "الفروع" : "Branches"}<input name="branches_limit" type="number" min="1" max="1000000" required defaultValue={Number(plan.limits.branches ?? 1)} /></label><label>{ar ? "التخزين (ميجابايت)" : "Storage (MB)"}<input name="storage_mb_limit" type="number" min="1" max="100000000" required defaultValue={Number(plan.limits.storage_mb ?? 1)} /></label></div></fieldset>
                  <fieldset className="plan-form-section"><legend>{ar ? "مزايا الباقة" : "Plan features"}</legend><div className="plan-feature-grid">{(["gps", "qr", "wifi", "tasks", "documents"] as const).map((feature) => <label className="checkbox-field" key={feature}><input type="checkbox" name={`feature_${feature}`} defaultChecked={Boolean(plan.features[feature])} />{feature === "gps" ? (ar ? "الحضور عبر نظام تحديد المواقع" : "GPS attendance") : feature === "qr" ? (ar ? "رمز الاستجابة السريعة" : "QR code") : feature === "wifi" ? (ar ? "الحضور عبر الشبكة اللاسلكية" : "Wi‑Fi attendance") : feature === "tasks" ? (ar ? "المهام" : "Tasks") : (ar ? "الوثائق والمرفقات" : "Documents and attachments")}</label>)}</div><label>{ar ? "مستوى التقارير" : "Reports level"}<select name="reports_level" defaultValue={String(plan.features.reports ?? "basic")}><option value="basic">{ar ? "أساسية" : "Basic"}</option><option value="advanced">{ar ? "متقدمة" : "Advanced"}</option></select></label></fieldset>
                  <label>{ar ? "مستوى الدعم" : "Support level"}<select name="support_level" defaultValue={plan.support_level} required><option value="community">{supportLabel("community", ar)}</option><option value="standard">{supportLabel("standard", ar)}</option><option value="priority">{supportLabel("priority", ar)}</option><option value="dedicated">{supportLabel("dedicated", ar)}</option></select></label>
                  <label>{ar ? "حالة الباقة" : "Plan status"}<select name="is_active" defaultValue={String(plan.is_active)}><option value="true">{ar ? "نشطة — تظهر للعملاء" : "Active — visible to customers"}</option><option value="false">{ar ? "غير نشطة — محفوظة ومخفية" : "Inactive — saved but hidden"}</option></select></label>
                  <button type="submit">{ar ? "تحديث الباقة" : "Update plan"}</button>
                </form>
              </details>
            ))}</div>
          </div>
          </div>
        </section>

        <section className="portal-section split-sections">
          <div>
            <h2>{ar ? "إنشاء كوبون" : "Create coupon"}</h2>
            <form action={createCouponAction.bind(null, lang)} className="portal-form">
              <input name="code" required placeholder="WELCOME20" />
              <select name="discount_type"><option value="percent">{couponTypeLabel("percent", ar)}</option><option value="fixed">{couponTypeLabel("fixed", ar)}</option></select>
              <input name="discount_value" type="number" min="1" required />
              <select name="plan_id" defaultValue=""><option value="">{ar ? "كل الباقات" : "All plans"}</option>{plans.map((plan) => <option key={plan.id} value={plan.id}>{planName(plan, ar)}</option>)}</select>
              <select name="billing_cycle" defaultValue=""><option value="">{ar ? "كل دورات الفوترة" : "All billing cycles"}</option><option value="monthly">{billingCycleLabel("monthly", ar)}</option><option value="annual">{billingCycleLabel("annual", ar)}</option></select>
              <input name="max_redemptions" type="number" min="1" placeholder={ar ? "الحد الأقصى" : "Maximum redemptions"} />
              <input name="valid_from" type="datetime-local" required />
              <input name="valid_until" type="datetime-local" required />
              <button type="submit">{ar ? "إنشاء" : "Create"}</button>
            </form>
          </div>
          <div>
            <h2>{ar ? "الكوبونات" : "Coupons"}</h2>
            <ul className="operation-list">{coupons.map((coupon) => <li key={coupon.id}><div><strong>{coupon.code}</strong><span>{coupon.discount_value}{coupon.discount_type === "percent" ? "%" : ` ${ar ? "وحدة" : "units"}`} · {coupon.redeemed_count}/{coupon.max_redemptions ?? "∞"}</span><small>{coupon.billing_cycle ? billingCycleLabel(coupon.billing_cycle, ar) : (ar ? "كل الدورات" : "All cycles")} · {coupon.valid_until}</small></div><span className="status-pill">{coupon.is_active ? (ar ? "نشط" : "Active") : (ar ? "غير نشط" : "Inactive")}</span></li>)}</ul>
          </div>
        </section>
      </section>
    </main>
  );
}
