import { authorizedApiFetch } from "@/lib/auth/server-session";

import {
  createReportExportAction,
  updateLeaderboardSettingsAction,
} from "./operations-actions";
import { reportTypeLabel, statusLabel } from "./display-labels";
import type { ReportFilters } from "./operations-dashboard";

type Employee = { membership_id: string; display_name: string };
type NamedOption = { id: string; name: string };
type DatasetReport = {
  items: Record<string, unknown>[];
  total: number;
  status_counts: Record<string, number>;
};
type ExportJob = {
  id: string;
  report_type: string;
  export_format: string;
  status: string;
  progress_percent: number;
  filename: string | null;
  created_at: string;
  expires_at: string;
  filters: Record<string, unknown>;
};
type LeaderboardItem = {
  rank: number;
  display_name: string;
  on_time_days: number;
  worked_minutes: number;
};
type LeaderboardSettings = { visibility: string; enabled: boolean; anonymize: boolean };

async function jsonOr<T>(path: string, fallback: T): Promise<T> {
  const response = await authorizedApiFetch(path);
  return response.ok ? ((await response.json()) as T) : fallback;
}

function employeeName(employees: Employee[], membershipId: string): string {
  return employees.find((item) => item.membership_id === membershipId)?.display_name ?? membershipId;
}

function reportTitle(item: Record<string, unknown>): string {
  return String(
    item.display_name ??
      item.title ??
      item.document_type ??
      item.request_type ??
      item.starts_on ??
      item.work_date ??
      item.id ??
      "",
  );
}

function exportDate(value: string, locale: string): string {
  return new Intl.DateTimeFormat(locale === "ar" ? "ar-SA" : "en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function exportPeriod(job: ExportJob, ar: boolean): string {
  const from = typeof job.filters?.date_from === "string" ? job.filters.date_from : "";
  const to = typeof job.filters?.date_to === "string" ? job.filters.date_to : "";
  if (from && to) return ar ? `الفترة: من ${from} إلى ${to}` : `Period: ${from} to ${to}`;
  if (from) return ar ? `الفترة: من ${from}` : `Period: from ${from}`;
  if (to) return ar ? `الفترة: حتى ${to}` : `Period: through ${to}`;
  return ar ? "الفترة: كل التواريخ" : "Period: all dates";
}

export async function ReportsDashboard({
  locale,
  employees,
  branches,
  departments,
  groups,
  reportFilters,
}: {
  locale: string;
  employees: Employee[];
  branches: NamedOption[];
  departments: NamedOption[];
  groups: NamedOption[];
  reportFilters: ReportFilters;
}) {
  const ar = locale === "ar";
  const reportParams = new URLSearchParams();
  for (const [key, value] of Object.entries(reportFilters)) {
    if (value) reportParams.set(key, value);
  }
  const reportSuffix = reportParams.size ? `?${reportParams.toString()}` : "";
  const leaderboardParams = new URLSearchParams();
  for (const key of ["date_from", "date_to", "branch_id", "department_id"] as const) {
    const value = reportFilters[key];
    if (value) leaderboardParams.set(key, value);
  }
  const leaderboardSuffix = leaderboardParams.size ? `?${leaderboardParams.toString()}` : "";
  const [
    exports,
    attendanceReport,
    geofenceReport,
    leaveReport,
    permissionReport,
    taskReport,
    documentReport,
    leaderboard,
    leaderboardSettings,
  ] = await Promise.all([
    jsonOr<ExportJob[]>("/reports/exports", []),
    jsonOr<DatasetReport>(`/reports/attendance${reportSuffix}`, { items: [], total: 0, status_counts: {} }),
    jsonOr<DatasetReport>(`/reports/geofence-exits${reportSuffix}`, { items: [], total: 0, status_counts: {} }),
    jsonOr<DatasetReport>(`/reports/leave${reportSuffix}`, { items: [], total: 0, status_counts: {} }),
    jsonOr<DatasetReport>(`/reports/permissions${reportSuffix}`, { items: [], total: 0, status_counts: {} }),
    jsonOr<DatasetReport>(`/reports/tasks${reportSuffix}`, { items: [], total: 0, status_counts: {} }),
    jsonOr<DatasetReport>(`/reports/documents${reportSuffix}`, { items: [], total: 0, status_counts: {} }),
    jsonOr<LeaderboardItem[]>(`/reports/leaderboard${leaderboardSuffix}`, []),
    jsonOr<LeaderboardSettings>("/reports/leaderboard/settings", {
      visibility: "disabled",
      enabled: false,
      anonymize: false,
    }),
  ]);
  const exportAction = createReportExportAction.bind(null, locale);
  const leaderboardAction = updateLeaderboardSettingsAction.bind(null, locale);
  const reportSections = [
    { key: "attendance", label: ar ? "الحضور والانصراف" : "Attendance", report: attendanceReport },
    { key: "geofence", label: ar ? "مغادرة النطاق" : "Geofence exits", report: geofenceReport },
    { key: "leave", label: ar ? "الإجازات" : "Leave", report: leaveReport },
    { key: "permissions", label: ar ? "الاستئذانات" : "Permissions", report: permissionReport },
    { key: "tasks", label: ar ? "المهام" : "Tasks", report: taskReport },
    { key: "documents", label: ar ? "الوثائق" : "Documents", report: documentReport },
  ];

  return (
    <>
      <section className="portal-section" aria-labelledby="reports-export-title">
        <div className="section-heading">
          <div>
            <h2 id="reports-export-title">{ar ? "طباعة وتصدير التقارير" : "Print and export reports"}</h2>
            <p>
              {ar
                ? "اختر تقرير الحضور والانصراف وحدد الفترة الأسبوعية أو الشهرية ثم PDF أو Excel."
                : "Choose attendance, select the weekly or monthly period, then PDF or Excel."}
            </p>
          </div>
        </div>
        <form action={exportAction} className="portal-form operation-form">
          <label>
            {ar ? "نوع التقرير" : "Report type"}
            <select name="report_type" defaultValue="attendance">
              {["attendance", "geofence_exits", "leave", "permissions", "tasks", "documents", "branches", "shifts"].map((type) => (
                <option key={type} value={type}>{reportTypeLabel(type, ar)}</option>
              ))}
            </select>
          </label>
          <fieldset className="report-type-checklist">
            <legend>{ar ? "أنواع إضافية في الملف نفسه" : "Additional types in the same file"}</legend>
            <div className="report-type-checklist-grid">
              {["attendance", "geofence_exits", "leave", "permissions", "tasks", "documents", "branches", "shifts"].map((type) => (
                <label className="checkbox-field" key={type}>
                  <input type="checkbox" name="report_types" value={type} />
                  <span>{reportTypeLabel(type, ar)}</span>
                </label>
              ))}
            </div>
          </fieldset>
          <label>
            {ar ? "الموظف" : "Employee"}
            <select name="membership_id" defaultValue="">
              <option value="">{ar ? "كل الموظفين" : "All employees"}</option>
              {employees.map((item) => <option key={item.membership_id} value={item.membership_id}>{item.display_name}</option>)}
            </select>
          </label>
          <label>
            {ar ? "صيغة الملف" : "File format"}
            <select name="export_format" defaultValue="pdf">
              <option value="pdf">PDF</option>
              <option value="xlsx">Excel/XLSX</option>
            </select>
          </label>
          <label>{ar ? "من تاريخ" : "From"}<input name="date_from" type="date" /></label>
          <label>{ar ? "إلى تاريخ" : "To"}<input name="date_to" type="date" /></label>
          <button type="submit">{ar ? "إنشاء ملف التقرير" : "Create report file"}</button>
        </form>
        {exports.length === 0 ? (
          <p className="empty-state">{ar ? "لا توجد ملفات تصدير بعد." : "No export files yet."}</p>
        ) : (
          <ul className="operation-list">
            {exports.map((job) => (
              <li key={job.id}>
                <div>
                  <strong>{reportTypeLabel(job.report_type, ar)} · {job.export_format === "xlsx" ? "Excel" : "PDF"}</strong>
                  <span>{statusLabel(job.status, ar)} · {job.progress_percent}%</span>
                  <small>{ar ? "تاريخ إنشاء الملف" : "File generated"}: {exportDate(job.created_at, locale)} · {exportPeriod(job, ar)}</small>
                  {job.filename && <small>{job.filename}</small>}
                </div>
                {job.status === "completed" && (
                  <a className="language-link" href={`/${locale}/exports/${job.id}`}>
                    {ar ? "تنزيل" : "Download"}
                  </a>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="portal-section" aria-labelledby="report-center-title">
        <div className="section-heading">
          <div>
            <h2 id="report-center-title">{ar ? "مركز التقارير" : "Report center"}</h2>
            <p>{ar ? "استعرض النتائج قبل إنشاء ملف PDF أو Excel." : "Review results before creating a PDF or Excel file."}</p>
          </div>
          <a className="language-link" href={`/${locale}/company?tab=reports`}>
            {ar ? "مسح الفلاتر" : "Clear filters"}
          </a>
        </div>
        <form method="get" action={`/${locale}/company`} className="portal-form operation-form">
          <input type="hidden" name="tab" value="reports" />
          <input name="report_date_from" type="date" defaultValue={reportFilters.date_from ?? ""} aria-label={ar ? "من تاريخ" : "From date"} />
          <input name="report_date_to" type="date" defaultValue={reportFilters.date_to ?? ""} aria-label={ar ? "إلى تاريخ" : "To date"} />
          <select name="report_membership_id" defaultValue={reportFilters.membership_id ?? ""}>
            <option value="">{ar ? "كل الموظفين" : "All employees"}</option>
            {employees.map((item) => <option key={item.membership_id} value={item.membership_id}>{item.display_name}</option>)}
          </select>
          <select name="report_branch_id" defaultValue={reportFilters.branch_id ?? ""}>
            <option value="">{ar ? "كل الفروع" : "All branches"}</option>
            {branches.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
          <select name="report_department_id" defaultValue={reportFilters.department_id ?? ""}>
            <option value="">{ar ? "كل الأقسام" : "All departments"}</option>
            {departments.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
          <select name="report_group_id" defaultValue={reportFilters.group_id ?? ""}>
            <option value="">{ar ? "كل المجموعات" : "All groups"}</option>
            {groups.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
          <input name="report_status" defaultValue={reportFilters.status ?? ""} placeholder={ar ? "الحالة اختياري" : "Status optional"} />
          <button type="submit">{ar ? "تطبيق الفلاتر" : "Apply filters"}</button>
        </form>
        <div className="metric-grid">
          {reportSections.map(({ key, label, report }) => (
            <details className="metric-card" key={key} open={key === "attendance"}>
              <summary><span>{label}</span><strong>{report.total}</strong></summary>
              <small>
                {Object.entries(report.status_counts).map(([status, count]) => `${statusLabel(status, ar)}: ${count}`).join(" · ") ||
                  (ar ? "لا توجد نتائج" : "No results")}
              </small>
              <ul className="operation-list">
                {report.items.slice(0, 10).map((item) => (
                  <li key={String(item.id)}>
                    <span>{reportTitle(item)}</span>
                    <small>
                      {statusLabel(String(item.status ?? ""), ar)}
                      {item.membership_id ? ` · ${employeeName(employees, String(item.membership_id))}` : ""}
                    </small>
                  </li>
                ))}
              </ul>
            </details>
          ))}
        </div>
      </section>

      <section className="portal-section split-sections">
        <div>
          <h3>{ar ? "ترتيب الحضور" : "Attendance ranking"}</h3>
          <ol className="operation-list">
            {leaderboard.map((item) => (
              <li key={`${item.rank}-${item.display_name}`}>
                <strong>#{item.rank} {item.display_name}</strong>
                <span>{item.on_time_days} {ar ? "أيام في الوقت" : "on-time days"} · {item.worked_minutes}m</span>
              </li>
            ))}
          </ol>
          {leaderboard.length === 0 && (
            <p className="empty-state">
              {ar ? "الترتيب معطل أو لا توجد بيانات ضمن الفترة." : "Ranking is disabled or no data matches the period."}
            </p>
          )}
        </div>
        <form action={leaderboardAction} className="portal-form operation-form">
          <h3>{ar ? "خصوصية الترتيب" : "Ranking privacy"}</h3>
          <label className="checkbox-field"><input type="checkbox" name="enabled" defaultChecked={leaderboardSettings.enabled} />{ar ? "تفعيل الترتيب" : "Enable ranking"}</label>
          <label className="checkbox-field"><input type="checkbox" name="anonymize" defaultChecked={leaderboardSettings.anonymize} />{ar ? "إخفاء أسماء الموظفين" : "Anonymize employee names"}</label>
          <select name="visibility" defaultValue={leaderboardSettings.visibility}>
            <option value="disabled">{ar ? "معطل" : "Disabled"}</option>
            <option value="manager_only">{ar ? "الإدارة فقط" : "Managers only"}</option>
            <option value="branch">{ar ? "نفس الفرع" : "Same branch"}</option>
            <option value="company">{ar ? "كل الشركة" : "Whole company"}</option>
          </select>
          <button type="submit">{ar ? "حفظ الخصوصية" : "Save privacy"}</button>
        </form>
      </section>
    </>
  );
}
