export function statusLabel(status: string | null | undefined, ar: boolean): string {
  const labels: Record<string, [string, string]> = {
    active: ["نشط", "Active"],
    inactive: ["غير نشط", "Inactive"],
    pending: ["قيد الانتظار", "Pending"],
    processing: ["قيد المعالجة", "Processing"],
    completed: ["مكتمل", "Completed"],
    failed: ["فشل", "Failed"],
    expired: ["منتهي", "Expired"],
    approved: ["مقبول", "Approved"],
    rejected: ["مرفوض", "Rejected"],
    valid: ["ساري", "Valid"],
    pending_review: ["بانتظار المراجعة", "Pending review"],
    on_time: ["حاضر في الوقت", "On time"],
    late: ["متأخر", "Late"],
    absent: ["غائب", "Absent"],
    on_permission: ["مستأذن", "On permission"],
    permission_return_late: ["عاد متأخرًا من الاستئذان", "Late return from permission"],
    on_leave: ["إجازة معتمدة", "Approved leave"],
    missing_checkout: ["لم يسجل الانصراف", "Missing check-out"],
    missing_check_out: ["لم يسجل الانصراف", "Missing check-out"],
    attendance_reminder: ["تذكير بإثبات الحضور", "Attendance reminder"],
    attendance_absent: ["تم تسجيل الغياب", "Absence recorded"],
    open: ["مفتوح", "Open"],
    viewed: ["تمت المشاهدة", "Viewed"],
    in_progress: ["قيد التنفيذ", "In progress"],
    needs_more_time: ["يحتاج وقتًا إضافيًا", "Needs more time"],
    blocked: ["متعطل", "Blocked"],
    postponed: ["مؤجل", "Postponed"],
    no_response: ["لم يرد", "No response"],
    responded: ["تم الرد", "Responded"],
  };
  const key = String(status ?? "").toLowerCase();
  return labels[key]?.[ar ? 0 : 1] ?? String(status ?? "—");
}

export function reportTypeLabel(type: string | null | undefined, ar: boolean): string {
  const labels: Record<string, [string, string]> = {
    attendance: ["الحضور والانصراف", "Attendance"],
    geofence_exits: ["الخروج من النطاق", "Unauthorized exits"],
    leave: ["الإجازات", "Leave"],
    permissions: ["الاستئذانات", "Permissions"],
    tasks: ["المهام", "Tasks"],
    documents: ["الوثائق", "Documents"],
    branches: ["الفروع", "Branches"],
    shifts: ["الورديات", "Shifts"],
    bundle: ["تقرير مجمع", "Combined report"],
  };
  const key = String(type ?? "");
  return labels[key]?.[ar ? 0 : 1] ?? key;
}

export function documentTypeLabel(type: string | null | undefined, ar: boolean): string {
  const labels: Record<string, [string, string]> = {
    residency: ["الإقامة", "Residency"],
    passport: ["جواز السفر", "Passport"],
    medical_insurance: ["التأمين الطبي", "Medical insurance"],
    employment_contract: ["عقد العمل", "Employment contract"],
    driving_license: ["رخصة القيادة", "Driving license"],
    vehicle_insurance: ["تأمين المركبة", "Vehicle insurance"],
    custom: ["نوع مخصص", "Custom"],
  };
  const key = String(type ?? "");
  return labels[key]?.[ar ? 0 : 1] ?? key;
}

export function priorityLabel(priority: string | null | undefined, ar: boolean): string {
  const labels: Record<string, [string, string]> = {
    low: ["منخفضة", "Low"],
    normal: ["عادية", "Normal"],
    high: ["عالية", "High"],
    urgent: ["عاجلة", "Urgent"],
  };
  const key = String(priority ?? "");
  return labels[key]?.[ar ? 0 : 1] ?? key;
}

export function permissionTypeLabel(type: string | null | undefined, ar: boolean): string {
  const labels: Record<string, [string, string]> = {
    one_hour: ["ساعة واحدة", "One hour"],
    multiple_hours: ["عدة ساعات", "Multiple hours"],
    custom: ["فترة مخصصة", "Custom"],
    until_shift_end: ["إلى نهاية الوردية", "Until shift end"],
  };
  const key = String(type ?? "");
  return labels[key]?.[ar ? 0 : 1] ?? key;
}

export function billingCycleLabel(cycle: string | null | undefined, ar: boolean): string {
  const labels: Record<string, [string, string]> = {
    monthly: ["شهري", "Monthly"],
    annual: ["سنوي", "Annual"],
    yearly: ["سنوي", "Yearly"],
  };
  const key = String(cycle ?? "");
  return labels[key]?.[ar ? 0 : 1] ?? key;
}

export function subscriptionLimitLabel(key: string, ar: boolean): string {
  const labels: Record<string, [string, string]> = {
    employees: ["حد الموظفين", "Employee limit"],
    branches: ["حد الفروع", "Branch limit"],
    storage_mb: ["مساحة التخزين", "Storage"],
  };
  return labels[key]?.[ar ? 0 : 1] ?? key;
}

export function formatLimitValue(key: string, value: unknown, ar: boolean): string {
  if (key === "storage_mb") return `${value} MB`;
  if (value === null || value === undefined || value === "") return ar ? "غير محدد" : "Not set";
  return String(value);
}
