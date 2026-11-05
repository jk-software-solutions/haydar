import Link from "next/link";
import { redirect } from "next/navigation";

import { authorizedApiFetch, getWebSession } from "@/lib/auth/server-session";
import { WhatsAppContact } from "@/components/whatsapp-contact";

import { SubscriptionPlanCard } from "./subscription-plan-card";
import { planName } from "./subscription-copy";

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

type Subscription = {
  plan: Plan;
  billing_cycle: string;
  status: string;
  starts_at: string;
  ends_at: string;
  limits_override: Record<string, unknown> | null;
};

type Request = {
  id: string;
  plan: Plan;
  billing_cycle: string;
  status: string;
  note: string | null;
  created_at: string;
};

async function jsonOr<T>(response: Response, fallback: T): Promise<T> {
  return response.ok ? ((await response.json()) as T) : fallback;
}

function dateLabel(value: string, locale: string): string {
  return new Intl.DateTimeFormat(locale === "ar" ? "ar-SA" : "en-GB", { dateStyle: "medium" }).format(new Date(value));
}

function statusLabel(value: string, ar: boolean): string {
  return ({
    active: ar ? "نشط" : "Active",
    trial: ar ? "تجريبي" : "Trial",
    pending: ar ? "بانتظار الاعتماد" : "Awaiting approval",
    approved: ar ? "تم الاعتماد" : "Approved",
    rejected: ar ? "مرفوض" : "Rejected",
  }[value] ?? value);
}

export default async function SubscriptionPage({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  const ar = lang === "ar";
  const session = await getWebSession();
  if (!session) redirect(`/${lang}/login`);
  const canManage = session.roles.some((role) => ["OWNER", "MANAGER", "HR_OFFICER"].includes(role));
  const [plansResponse, subscriptionResponse, requestsResponse, providerResponse, platformResponse] = await Promise.all([
    authorizedApiFetch("/billing/plans"),
    authorizedApiFetch("/billing/subscription"),
    authorizedApiFetch("/billing/subscription-requests"),
    authorizedApiFetch("/billing/payment-provider"),
    authorizedApiFetch("/platform/dashboard"),
  ]);
  const plans = await jsonOr<Plan[]>(plansResponse, []);
  const subscription = await jsonOr<Subscription | null>(subscriptionResponse, null);
  const requests = await jsonOr<Request[]>(requestsResponse, []);
  const provider = await jsonOr<{ configured: boolean; provider: string | null }>(providerResponse, { configured: false, provider: null });
  const featuredIndex = plans.length > 1 ? 1 : 0;

  return (
    <main className="subscription-page-shell">
      <section className="subscription-page-card">
        <header className="subscription-page-header">
          <div>
            <p className="foundation-eyebrow">DawamTech | دوام تك</p>
            <h1>{ar ? "اختر الاشتراك المناسب لشركتك" : "Choose the right plan for your company"}</h1>
            <p>{ar ? "فعّل أدوات الحضور والموظفين والتقارير بخطوات واضحة، وغيّر الباقة عندما يكبر عملك." : "Activate attendance, workforce, and reporting tools with a clear plan that can grow with your company."}</p>
          </div>
          <div className="subscription-page-actions">
            <WhatsAppContact lang={lang} />
            <Link className="language-link secondary" href={`/${lang}/company`}>{ar ? "لوحة الشركة" : "Company portal"}</Link>
            {platformResponse.ok && <Link className="language-link" href={`/${lang}/platform`}>{ar ? "لوحة مالك التطبيق" : "Platform owner"}</Link>}
          </div>
        </header>

        {subscription ? (
          <section className="subscription-current-card">
            <div><span className="status-pill">{statusLabel(subscription.status, ar)}</span><h2>{planName(subscription.plan, ar)}</h2><p>{ar ? "اشتراك شركتك الحالي" : "Your company’s current subscription"}</p></div>
            <div><span>{ar ? "ينتهي في" : "Ends"}</span><strong>{dateLabel(subscription.ends_at, lang)}</strong></div>
            <Link className="language-link secondary" href={`/${lang}/company?tab=operations`}>{ar ? "عرض التفاصيل" : "View details"}</Link>
          </section>
        ) : (
          <section className="subscription-notice"><strong>{ar ? "لا يوجد اشتراك فعال" : "No active subscription"}</strong><span>{ar ? "اختر باقة وأرسل طلب التفعيل من الأسفل." : "Choose a plan and submit an activation request below."}</span></section>
        )}

        {!provider.configured && <p className="subscription-payment-note">{ar ? "الدفع الإلكتروني غير مفعّل حاليًا. بعد اختيار الباقة سيصل الطلب إلى مالك المنصة لاعتماد الدفع وتفعيل الاشتراك." : "Online payment is not configured yet. After you choose a plan, the request goes to the platform owner for payment confirmation and activation."}</p>}

        <section className="subscription-plans-heading"><div><h2>{ar ? "الباقات" : "Plans"}</h2><p>{ar ? "أسعار واضحة وحدود ظاهرة قبل الإرسال." : "Clear pricing and visible limits before you submit."}</p></div><span>{plans.length} {ar ? "باقات متاحة" : "plans available"}</span></section>
        {canManage ? (
          <section className="subscription-plan-grid">
            {plans.map((plan, index) => <SubscriptionPlanCard key={plan.id} plan={plan} locale={lang} featured={index === featuredIndex} />)}
          </section>
        ) : (
          <p className="subscription-notice">{ar ? "يمكن لمالك الشركة أو المدير المفوض فقط طلب تغيير الاشتراك." : "Only the company owner or an authorized manager can request a subscription change."}</p>
        )}

        <section className="subscription-request-history">
          <div className="subscription-plans-heading"><div><h2>{ar ? "طلباتك السابقة" : "Your requests"}</h2><p>{ar ? "تابع حالة طلب التفعيل من مكان واحد." : "Track activation requests in one place."}</p></div></div>
          {requests.length === 0 ? <p className="empty-state">{ar ? "لا توجد طلبات اشتراك بعد." : "No subscription requests yet."}</p> : <div className="subscription-request-list">{requests.map((item) => <article key={item.id}><div><strong>{planName(item.plan, ar)}</strong><span>{item.billing_cycle === "annual" ? (ar ? "سنوي" : "Annual") : (ar ? "شهري" : "Monthly")} · {dateLabel(item.created_at, lang)}</span></div><span className="status-pill">{statusLabel(item.status, ar)}</span></article>)}</div>}
        </section>
      </section>
    </main>
  );
}
