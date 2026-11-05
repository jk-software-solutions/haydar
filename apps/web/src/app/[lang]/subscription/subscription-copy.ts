type LocalizablePlan = {
  code: string;
  name: string;
  description?: string;
  support_level?: string;
};

const standardPlanNames: Record<string, { ar: string; en: string }> = {
  FREE_TRIAL: { ar: "التجربة المجانية", en: "Free Trial" },
  BASIC: { ar: "الباقة الأساسية", en: "Basic" },
  PROFESSIONAL: { ar: "الباقة الاحترافية", en: "Professional" },
  ENTERPRISE: { ar: "باقة المؤسسات", en: "Enterprise" },
};

const standardPlanDescriptions: Record<string, { ar: string; en: string }> = {
  FREE_TRIAL: { ar: "باقة للتجربة والتقييم", en: "Evaluation plan" },
  BASIC: { ar: "للشركات والفرق الصغيرة", en: "Small teams" },
  PROFESSIONAL: { ar: "للمنشآت المتنامية", en: "Growing organizations" },
  ENTERPRISE: { ar: "باقة مخصصة للمؤسسات", en: "Custom enterprise plan" },
};

export function planName(plan: LocalizablePlan, ar: boolean): string {
  return standardPlanNames[plan.code.toUpperCase()]?.[ar ? "ar" : "en"] ?? plan.name;
}

export function planDescription(plan: LocalizablePlan, ar: boolean): string {
  return standardPlanDescriptions[plan.code.toUpperCase()]?.[ar ? "ar" : "en"] ?? plan.description ?? "";
}

export function supportLabel(value: string, ar: boolean): string {
  const labels: Record<string, { ar: string; en: string }> = {
    community: { ar: "مجتمعي", en: "Community" },
    standard: { ar: "قياسي", en: "Standard" },
    priority: { ar: "أولوية", en: "Priority" },
    dedicated: { ar: "مخصص", en: "Dedicated" },
  };
  return labels[value.toLowerCase()]?.[ar ? "ar" : "en"] ?? value;
}

export function limitLabel(key: string, ar: boolean): string {
  const labels: Record<string, { ar: string; en: string }> = {
    employees: { ar: "الموظفون", en: "Employees" },
    branches: { ar: "الفروع", en: "Branches" },
    storage_mb: { ar: "ميجابايت تخزين", en: "MB storage" },
  };
  return labels[key]?.[ar ? "ar" : "en"] ?? key.replaceAll("_", " ");
}

export function featureLabel(key: string, ar: boolean): string {
  const labels: Record<string, { ar: string; en: string }> = {
    gps: { ar: "الحضور عبر نظام تحديد المواقع", en: "GPS attendance" },
    qr: { ar: "رموز الاستجابة السريعة", en: "QR codes" },
    wifi: { ar: "التحقق عبر الشبكة اللاسلكية", en: "Wi‑Fi verification" },
    tasks: { ar: "إدارة المهام", en: "Task management" },
    documents: { ar: "المرفقات والوثائق", en: "Documents and attachments" },
    reports: { ar: "التقارير", en: "Reports" },
  };
  return labels[key]?.[ar ? "ar" : "en"] ?? key.replaceAll("_", " ");
}

export function featureValue(value: unknown, ar: boolean): string | null {
  if (typeof value !== "string") return null;
  const labels: Record<string, { ar: string; en: string }> = {
    basic: { ar: "أساسية", en: "Basic" },
    advanced: { ar: "متقدمة", en: "Advanced" },
  };
  return labels[value.toLowerCase()]?.[ar ? "ar" : "en"] ?? value;
}
