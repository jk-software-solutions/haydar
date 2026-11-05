import {
  createDocumentAction,
  createLeaveRequestAction,
  createLeaveTypeAction,
  createManualAttendanceAction,
  createPermissionAction,
  createPresenceRequestAction,
  createReportExportAction,
  createTaskAction,
  deleteDocumentAction,
  decideTaskExtensionAction,
  reviewDocumentAction,
  reviewLeaveAction,
  reviewPermissionAction,
  setLeaveBalanceAction,
  updateDocumentAction,
  updateLeaderboardSettingsAction,
  updateTaskStatusAction,
} from "./operations-actions";
import { QrTokenForm } from "./qr-token-form";
import { FileUploadForm } from "./file-upload-form";
import { authorizedApiFetch } from "@/lib/auth/server-session";
import {
  billingCycleLabel,
  documentTypeLabel,
  formatLimitValue,
  permissionTypeLabel,
  priorityLabel,
  reportTypeLabel,
  statusLabel,
  subscriptionLimitLabel,
} from "./display-labels";

type Employee = { membership_id: string; display_name: string; role_code: string; membership_status: string };
type Branch = { id: string; name: string };
type Shift = {
  id: string;
  name: string;
  start_time: string;
  end_time: string;
  recurrence?: { periods?: { start_time?: string; end_time?: string }[] };
};
type NamedOption = { id: string; name: string };
export type ReportFilters = {
  date_from?: string;
  date_to?: string;
  membership_id?: string;
  branch_id?: string;
  department_id?: string;
  group_id?: string;
  status?: string;
};
type DatasetReport = {
  items: Record<string, unknown>[];
  total: number;
  status_counts: Record<string, number>;
};
type LeaderboardItem = { rank: number; display_name: string; on_time_days: number; worked_minutes: number };
type LeaderboardSettings = { visibility: string; enabled: boolean; anonymize: boolean };
type Overview = {
  employees: number;
  branches: number;
  shifts: number;
  attendance_records: number;
  pending_leave_requests: number;
  pending_permission_requests: number;
  open_tasks: number;
  expired_documents: number;
  expiring_documents: number;
  unauthorized_geofence_exits: number;
};
type Attendance = {
  id: string;
  membership_id: string;
  shift_id: string;
  work_date: string;
  status: string;
  checked_in_at: string | null;
  checked_out_at: string | null;
  worked_minutes: number;
  late_minutes: number;
  is_manual: boolean;
};
type PresenceResult = {
  id: string;
  request_id: string;
  membership_id: string;
  message: string;
  deadline_at: string;
  status: string;
  responded_at: string | null;
  distance_m: number | null;
  note: string | null;
};
type Task = {
  id: string;
  title: string;
  priority: string;
  status: string;
  due_at: string | null;
  assignee_ids: string[];
  completion_attachment_file_id: string | null;
  version: number;
  latest_extension: {
    reason: string;
    requested_due_at: string | null;
    status: string;
    decision_comment: string | null;
  } | null;
};
type PermissionRequest = {
  id: string;
  membership_id: string;
  request_type: string;
  starts_at: string;
  ends_at: string;
  reason: string;
  attachment_file_id: string | null;
  status: string;
};
type LeaveType = { id: string; code: string; name: string; default_days: number };
type LeaveRequest = {
  id: string;
  membership_id: string;
  starts_on: string;
  ends_on: string;
  days: number;
  reason: string;
  status: string;
};
type Document = {
  id: string;
  membership_id: string;
  document_type: string;
  custom_type_name: string | null;
  document_number: string | null;
  issued_on: string | null;
  expires_on: string | null;
  status: string;
  review_status: string;
  attachment_file_id: string;
  reminder_days: number;
  version: number;
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
type Subscription = {
  status: string;
  billing_cycle: string;
  ends_at: string;
  limits_override?: Record<string, unknown> | null;
  plan: { name: string; code: string; limits: Record<string, unknown>; features: Record<string, unknown> };
};

async function jsonOr<T>(path: string, fallback: T): Promise<T> {
  const response = await authorizedApiFetch(path);
  return response.ok ? ((await response.json()) as T) : fallback;
}

function employeeName(employees: Employee[], membershipId: string): string {
  return employees.find((item) => item.membership_id === membershipId)?.display_name ?? membershipId;
}

function formatDate(value: string | null, locale: string): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat(locale === "ar" ? "ar-SA" : "en-GB", {
    dateStyle: "medium",
    timeStyle: value.includes("T") ? "short" : undefined,
  }).format(new Date(value));
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

function formatTime(value: string | null, locale: string): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat(locale === "ar" ? "ar-SA" : "en-GB", {
    timeStyle: "short",
  }).format(new Date(value));
}

function shiftPeriods(shift: Shift | undefined): { start: string; end: string }[] {
  const periods = shift?.recurrence?.periods
    ?.filter((period) => period.start_time && period.end_time)
    .map((period) => ({ start: period.start_time!, end: period.end_time! }));
  return periods?.length ? periods : shift ? [{ start: shift.start_time, end: shift.end_time }] : [];
}

const reportExportTypes = ["attendance", "geofence_exits", "leave", "permissions", "tasks", "documents", "branches", "shifts"];
const documentTypes = ["residency", "passport", "medical_insurance", "employment_contract", "driving_license", "vehicle_insurance", "custom"];

export async function OperationsDashboard({
  locale,
  canManage,
  employees,
  taskRecipients = [],
  branches,
  shifts,
  departments,
  groups,
  reportFilters,
}: {
  locale: string;
  canManage: boolean;
  employees: Employee[];
  taskRecipients?: NamedOption[];
  branches: Branch[];
  shifts: Shift[];
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
    overview,
    attendance,
    presenceResults,
    tasks,
    permissions,
    leaveTypes,
    leaveRequests,
    documents,
    exports,
    subscription,
    attendanceReport,
    geofenceReport,
    leaveReport,
    permissionReport,
    taskReport,
    documentReport,
    leaderboard,
    leaderboardSettings,
  ] =
    await Promise.all([
      canManage ? jsonOr<Overview | null>("/reports/overview", null) : Promise.resolve(null),
      jsonOr<Attendance[]>(canManage ? "/attendance" : "/attendance/me", []),
      canManage ? jsonOr<PresenceResult[]>("/presence-requests", []) : Promise.resolve([]),
      jsonOr<Task[]>(canManage ? "/tasks" : "/tasks?mine=true", []),
      jsonOr<PermissionRequest[]>(canManage ? "/permission-requests" : "/permission-requests?mine=true", []),
      jsonOr<LeaveType[]>("/leave/types", []),
      jsonOr<LeaveRequest[]>(canManage ? "/leave/requests" : "/leave/requests?mine=true", []),
      jsonOr<Document[]>("/documents", []),
      canManage ? jsonOr<ExportJob[]>("/reports/exports", []) : Promise.resolve([]),
      jsonOr<Subscription | null>("/billing/subscription", null),
      canManage ? jsonOr<DatasetReport>(`/reports/attendance${reportSuffix}`, { items: [], total: 0, status_counts: {} }) : Promise.resolve({ items: [], total: 0, status_counts: {} }),
      canManage ? jsonOr<DatasetReport>(`/reports/geofence-exits${reportSuffix}`, { items: [], total: 0, status_counts: {} }) : Promise.resolve({ items: [], total: 0, status_counts: {} }),
      canManage ? jsonOr<DatasetReport>(`/reports/leave${reportSuffix}`, { items: [], total: 0, status_counts: {} }) : Promise.resolve({ items: [], total: 0, status_counts: {} }),
      canManage ? jsonOr<DatasetReport>(`/reports/permissions${reportSuffix}`, { items: [], total: 0, status_counts: {} }) : Promise.resolve({ items: [], total: 0, status_counts: {} }),
      canManage ? jsonOr<DatasetReport>(`/reports/tasks${reportSuffix}`, { items: [], total: 0, status_counts: {} }) : Promise.resolve({ items: [], total: 0, status_counts: {} }),
      canManage ? jsonOr<DatasetReport>(`/reports/documents${reportSuffix}`, { items: [], total: 0, status_counts: {} }) : Promise.resolve({ items: [], total: 0, status_counts: {} }),
      canManage ? jsonOr<LeaderboardItem[]>(`/reports/leaderboard${leaderboardSuffix}`, []) : Promise.resolve([]),
      canManage ? jsonOr<LeaderboardSettings>("/reports/leaderboard/settings", { visibility: "disabled", enabled: false, anonymize: false }) : Promise.resolve({ visibility: "disabled", enabled: false, anonymize: false }),
    ]);

  const taskAction = createTaskAction.bind(null, locale);
  const permissionAction = createPermissionAction.bind(null, locale);
  const leaveTypeAction = createLeaveTypeAction.bind(null, locale);
  const balanceAction = setLeaveBalanceAction.bind(null, locale);
  const leaveAction = createLeaveRequestAction.bind(null, locale);
  const documentAction = createDocumentAction.bind(null, locale);
  const manualAttendanceAction = createManualAttendanceAction.bind(null, locale);
  const presenceAction = createPresenceRequestAction.bind(null, locale);
  const exportAction = createReportExportAction.bind(null, locale);
  const leaderboardAction = updateLeaderboardSettingsAction.bind(null, locale);
  const reportSections = [
    { key: "attendance", label: ar ? "الحضور" : "Attendance", report: attendanceReport },
    { key: "geofence", label: ar ? "مغادرة النطاق" : "Geofence exits", report: geofenceReport },
    { key: "leave", label: ar ? "الإجازات" : "Leave", report: leaveReport },
    { key: "permissions", label: ar ? "الاستئذانات" : "Permissions", report: permissionReport },
    { key: "tasks", label: ar ? "المهام" : "Tasks", report: taskReport },
    { key: "documents", label: ar ? "الوثائق" : "Documents", report: documentReport },
  ];
  const shiftById = new Map(shifts.map((shift) => [shift.id, shift]));

  return (
    <>
      {overview && (
        <section className="portal-section" aria-labelledby="operations-overview">
          <h2 id="operations-overview">{ar ? "نظرة عامة على العمليات" : "Operations overview"}</h2>
          <div className="metric-grid">
            {[
              [ar ? "الموظفون" : "Employees", overview.employees],
              [ar ? "سجلات الحضور" : "Attendance records", overview.attendance_records],
              [ar ? "المهام المفتوحة" : "Open tasks", overview.open_tasks],
              [ar ? "طلبات الإجازة" : "Pending leave", overview.pending_leave_requests],
              [ar ? "طلبات الاستئذان" : "Pending permissions", overview.pending_permission_requests],
              [ar ? "وثائق منتهية" : "Expired documents", overview.expired_documents],
              [ar ? "مغادرة غير مصرح بها" : "Unauthorized exits", overview.unauthorized_geofence_exits],
            ].map(([label, value]) => (
              <article className="metric-card" key={String(label)}>
                <span>{label}</span>
                <strong>{value}</strong>
              </article>
            ))}
          </div>
        </section>
      )}

      <section className="portal-section" aria-labelledby="attendance-title">
        <div className="section-heading">
          <div>
            <h2 id="attendance-title">{ar ? "الحضور والانصراف" : "Attendance"}</h2>
            <p>{ar ? "السجلات الفعلية المحسوبة من الخادم." : "Server-calculated attendance records."}</p>
          </div>
          <span className="status-pill">{attendance.length}</span>
        </div>
        {canManage && (
          <><QrTokenForm locale={locale} branches={branches} /><details className="operation-form-card">
            <summary>{ar ? "إضافة حضور يدوي" : "Add manual attendance"}</summary>
            <form action={manualAttendanceAction} className="portal-form inline">
              <select name="membership_id" required aria-label={ar ? "الموظف" : "Employee"}>
                <option value="">{ar ? "اختر الموظف" : "Select employee"}</option>
                {employees.map((employee) => <option key={employee.membership_id} value={employee.membership_id}>{employee.display_name}</option>)}
              </select>
              <select name="branch_id" required aria-label={ar ? "الفرع" : "Branch"}>
                <option value="">{ar ? "اختر الفرع" : "Select branch"}</option>
                {branches.map((branch) => <option key={branch.id} value={branch.id}>{branch.name}</option>)}
              </select>
              <select name="shift_id" required aria-label={ar ? "الوردية" : "Shift"}>
                <option value="">{ar ? "اختر الوردية" : "Select shift"}</option>
                {shifts.map((shift) => <option key={shift.id} value={shift.id}>{shift.name}</option>)}
              </select>
              <input name="work_date" type="date" required aria-label={ar ? "التاريخ" : "Date"} />
              <input name="checked_in_at" type="datetime-local" required aria-label={ar ? "وقت الحضور" : "Check-in"} />
              <input name="checked_out_at" type="datetime-local" aria-label={ar ? "وقت الانصراف" : "Check-out"} />
              <input name="reason" required minLength={5} placeholder={ar ? "سبب التسجيل اليدوي" : "Reason for manual entry"} />
              <button type="submit">{ar ? "حفظ السجل" : "Save record"}</button>
            </form>
          </details><details className="operation-form-card"><summary>{ar ? "إرسال طلب إثبات تواجد" : "Send presence challenge"}</summary><form action={presenceAction} className="portal-form inline"><select name="membership_ids" required><option value="">{ar ? "اختر الموظف" : "Select employee"}</option>{employees.map((employee) => <option key={employee.membership_id} value={employee.membership_id}>{employee.display_name}</option>)}</select><input name="message" required defaultValue={ar ? "يرجى تأكيد تواجدك في الفرع الآن" : "Please confirm your presence at the branch now"} /><input name="deadline_seconds" type="number" min="30" max="3600" defaultValue="300" /><button type="submit">{ar ? "إرسال عاجل" : "Send urgent request"}</button></form></details></>
        )}
        <div className="data-table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>{ar ? "الموظف" : "Employee"}</th>
                <th>{ar ? "الفترة 1 حضور" : "Period 1 in"}</th>
                <th>{ar ? "الفترة 1 انصراف" : "Period 1 out"}</th>
                <th>{ar ? "الفترة 2 حضور" : "Period 2 in"}</th>
                <th>{ar ? "الفترة 2 انصراف" : "Period 2 out"}</th>
                <th>{ar ? "ملاحظات" : "Notes"}</th>
              </tr>
            </thead>
            <tbody>{attendance.slice(0, 50).map((item) => {
              const periods = shiftPeriods(shiftById.get(item.shift_id));
              return (
                <tr key={item.id}>
                  <td>{employeeName(employees, item.membership_id)}<br /><small>{formatDate(item.work_date, locale)}</small></td>
                  <td>{formatTime(item.checked_in_at, locale)}<br /><small>{periods[0]?.start?.slice(0, 5) ?? "—"}</small></td>
                  <td>{formatTime(item.checked_out_at, locale)}<br /><small>{periods[0]?.end?.slice(0, 5) ?? "—"}</small></td>
                  <td>—<br /><small>{periods[1]?.start?.slice(0, 5) ?? "—"}</small></td>
                  <td>—<br /><small>{periods[1]?.end?.slice(0, 5) ?? "—"}</small></td>
                  <td><span className="status-pill">{statusLabel(item.status, ar)}</span>{item.is_manual ? ` · ${ar ? "يدوي" : "Manual"}` : ""} · {ar ? "تأخير" : "Late"} {item.late_minutes}m · {ar ? "عمل" : "Worked"} {item.worked_minutes}m</td>
                </tr>
              );
            })}</tbody>
          </table>
          {attendance.length === 0 && <p className="empty-state">{ar ? "لا توجد سجلات حضور بعد." : "No attendance records yet."}</p>}
        </div>
      </section>

      {canManage && (
        <section className="portal-section" aria-labelledby="presence-title">
          <div className="section-heading"><h2 id="presence-title">{ar ? "إثبات التواجد" : "Proof of Presence"}</h2><span className="status-pill">{presenceResults.length}</span></div>
          <p>{ar ? "استهدف موظفاً أو فرعاً أو مجموعة، ثم راقب الرد والمسافة أو عدم الاستجابة." : "Target an employee, branch, or group, then review response distance or no-response status."}</p>
          <form action={presenceAction} className="portal-form operation-form">
            <select name="membership_ids"><option value="">{ar ? "بدون موظف محدد" : "No individual employee"}</option>{employees.map((employee) => <option key={employee.membership_id} value={employee.membership_id}>{employee.display_name}</option>)}</select>
            <select name="branch_id"><option value="">{ar ? "بدون فرع" : "No branch"}</option>{branches.map((branch) => <option key={branch.id} value={branch.id}>{branch.name}</option>)}</select>
            <select name="group_id"><option value="">{ar ? "بدون مجموعة" : "No group"}</option>{groups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}</select>
            <input name="message" required defaultValue={ar ? "يرجى تأكيد تواجدك في الفرع الآن" : "Please confirm your presence at the branch now"} />
            <label>{ar ? "مهلة الرد بالثواني" : "Response deadline (seconds)"}<input name="deadline_seconds" type="number" min="30" max="3600" defaultValue="300" /></label>
            <button type="submit">{ar ? "إرسال طلب عاجل" : "Send urgent request"}</button>
          </form>
          <div className="data-table-wrap">
            <table className="data-table"><thead><tr><th>{ar ? "الموظف" : "Employee"}</th><th>{ar ? "الحالة" : "Status"}</th><th>{ar ? "المهلة" : "Deadline"}</th><th>{ar ? "المسافة" : "Distance"}</th></tr></thead><tbody>{presenceResults.map((item) => <tr key={item.id}><td>{employeeName(employees, item.membership_id)}</td><td><span className="status-pill">{statusLabel(item.status, ar)}</span></td><td>{formatDate(item.deadline_at, locale)}</td><td>{item.distance_m === null ? "—" : `${item.distance_m}m`}</td></tr>)}</tbody></table>
            {presenceResults.length === 0 && <p className="empty-state">{ar ? "لا توجد طلبات إثبات تواجد بعد." : "No presence challenges yet."}</p>}
          </div>
        </section>
      )}

      <section className="portal-section" aria-labelledby="tasks-title">
        <div className="section-heading"><h2 id="tasks-title">{ar ? "المهام" : "Tasks"}</h2><span className="status-pill">{tasks.length}</span></div>
        {(canManage || taskRecipients.length > 0) && (
          <form action={taskAction} className="portal-form operation-form">
            <input name="title" required placeholder={ar ? "عنوان المهمة" : "Task title"} />
            <textarea name="description" required placeholder={ar ? "الوصف" : "Description"} />
            <select name="priority" defaultValue="normal"><option value="low">{priorityLabel("low", ar)}</option><option value="normal">{priorityLabel("normal", ar)}</option><option value="high">{priorityLabel("high", ar)}</option><option value="urgent">{priorityLabel("urgent", ar)}</option></select>
            <input name="due_at" type="datetime-local" aria-label={ar ? "موعد التسليم" : "Due date"} />
            <select name="membership_ids" required aria-label={ar ? "إرسال إلى" : "Send to"}><option value="">{ar ? "اختر المستلم" : "Select recipient"}</option>{(canManage ? employees.filter((employee) => employee.membership_status === "active" && employee.role_code !== "OWNER").map((employee) => ({ id: employee.membership_id, name: employee.display_name })) : taskRecipients).map((recipient) => <option key={recipient.id} value={recipient.id}>{recipient.name}</option>)}</select>
            <button type="submit">{canManage ? (ar ? "إرسال المهمة" : "Send task") : (ar ? "إرسال طلب للمدير" : "Send request to manager")}</button>
          </form>
        )}
        <div className="kanban-grid">
          {tasks.map((task) => {
            const statusAction = updateTaskStatusAction.bind(null, locale, task.id, task.version);
            return (
              <article className="task-card" key={task.id}>
                <div className="section-heading"><strong>{task.title}</strong><span className={`status-pill ${task.priority === "urgent" ? "urgent" : ""}`}>{priorityLabel(task.priority, ar)}</span></div>
                <p>{statusLabel(task.status, ar)} · {formatDate(task.due_at, locale)}</p>
                <small>{task.assignee_ids.map((id) => employeeName(employees, id)).join(", ")}</small>
                {task.completion_attachment_file_id && (
                  <a className="language-link" href={`/api/files/${task.completion_attachment_file_id}`}>
                    {ar ? "تنزيل الإيصال المرفق" : "Download attached receipt"}
                  </a>
                )}
                <form action={statusAction} className="inline-action">
                  <select name="status" defaultValue={task.status}><option value="viewed">{statusLabel("viewed", ar)}</option><option value="in_progress">{statusLabel("in_progress", ar)}</option><option value="completed">{statusLabel("completed", ar)}</option><option value="needs_more_time">{statusLabel("needs_more_time", ar)}</option><option value="blocked">{statusLabel("blocked", ar)}</option><option value="postponed">{statusLabel("postponed", ar)}</option></select>
                  <input name="reason" placeholder={ar ? "السبب عند الحاجة" : "Reason when required"} />
                  <input name="requested_due_at" type="datetime-local" aria-label={ar ? "الموعد المطلوب للتمديد" : "Requested extension due date"} />
                  <button type="submit">{ar ? "تحديث" : "Update"}</button>
                </form>
                {canManage && task.latest_extension?.status === "pending" && (
                  <aside className="operation-form-card">
                    <strong>{ar ? "طلب وقت إضافي" : "Extension request"}</strong>
                    <p>{task.latest_extension.reason} · {formatDate(task.latest_extension.requested_due_at, locale)}</p>
                    <div className="button-row">
                      <form action={decideTaskExtensionAction.bind(null, locale, task.id, task.version, "approved")} className="inline-action">
                        <input name="new_due_at" type="datetime-local" required />
                        <input name="comment" required minLength={2} placeholder={ar ? "تعليق الموافقة" : "Approval comment"} />
                        <button type="submit">{ar ? "الموافقة والتمديد" : "Approve extension"}</button>
                      </form>
                      <form action={decideTaskExtensionAction.bind(null, locale, task.id, task.version, "rejected")} className="inline-action">
                        <input name="comment" required minLength={2} placeholder={ar ? "سبب الرفض" : "Rejection reason"} />
                        <button type="submit" className="danger-button">{ar ? "رفض التمديد" : "Reject extension"}</button>
                      </form>
                    </div>
                  </aside>
                )}
              </article>
            );
          })}
          {tasks.length === 0 && <p className="empty-state">{ar ? "لا توجد مهام." : "No tasks."}</p>}
        </div>
      </section>

      <section className="portal-section split-sections">
        <div>
          <h2>{ar ? "الاستئذان" : "Permission requests"}</h2>
          <form action={permissionAction} className="portal-form operation-form">
            <select name="request_type" defaultValue="one_hour"><option value="one_hour">{permissionTypeLabel("one_hour", ar)}</option><option value="multiple_hours">{permissionTypeLabel("multiple_hours", ar)}</option><option value="custom">{permissionTypeLabel("custom", ar)}</option><option value="until_shift_end">{permissionTypeLabel("until_shift_end", ar)}</option></select>
            <input name="starts_at" type="datetime-local" required />
            <input name="ends_at" type="datetime-local" />
            <small>{ar ? "اترك وقت النهاية فارغاً عند اختيار إلى نهاية الوردية." : "Leave end time empty when choosing until shift end."}</small>
            <input name="reason" required placeholder={ar ? "السبب" : "Reason"} />
            <button type="submit">{ar ? "إرسال الطلب" : "Submit request"}</button>
          </form>
          <ul className="operation-list">{permissions.map((item) => <li key={item.id}><div><strong>{employeeName(employees, item.membership_id)}</strong><span>{permissionTypeLabel(item.request_type, ar)} · {statusLabel(item.status, ar)}</span><small>{item.reason}</small>{item.attachment_file_id && <a className="language-link" href={`/api/files/${item.attachment_file_id}`}>{ar ? "فتح المرفق" : "Open attachment"}</a>}</div>{canManage && item.status === "pending" && <div className="button-row"><form action={reviewPermissionAction.bind(null, locale, item.id, "approved")}><button type="submit">{ar ? "قبول" : "Approve"}</button></form><form action={reviewPermissionAction.bind(null, locale, item.id, "rejected")}><button type="submit" className="danger-button">{ar ? "رفض" : "Reject"}</button></form></div>}</li>)}</ul>
        </div>
        <div>
          <h2>{ar ? "الإجازات" : "Leave"}</h2>
          <form action={leaveAction} className="portal-form operation-form">
            <select name="leave_type_id" required><option value="">{ar ? "نوع الإجازة" : "Leave type"}</option>{leaveTypes.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
            <input name="starts_on" type="date" required /><input name="ends_on" type="date" required />
            <input name="reason" required placeholder={ar ? "السبب" : "Reason"} /><button type="submit">{ar ? "إرسال الطلب" : "Submit request"}</button>
          </form>
          {canManage && <details className="operation-form-card"><summary>{ar ? "إعداد أنواع وأرصدة الإجازة" : "Configure leave types and balances"}</summary><form action={leaveTypeAction} className="portal-form inline"><input name="code" required placeholder="ANNUAL" /><input name="name" required placeholder={ar ? "إجازة سنوية" : "Annual leave"} /><input name="default_days" type="number" min="0" max="365" required /><label className="checkbox-field"><input name="is_paid" type="checkbox" defaultChecked />{ar ? "مدفوعة" : "Paid"}</label><button type="submit">{ar ? "إضافة النوع" : "Add type"}</button></form><form action={balanceAction} className="portal-form inline"><select name="membership_id" required><option value="">{ar ? "الموظف" : "Employee"}</option>{employees.map((employee) => <option key={employee.membership_id} value={employee.membership_id}>{employee.display_name}</option>)}</select><select name="leave_type_id" required><option value="">{ar ? "النوع" : "Type"}</option>{leaveTypes.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select><input name="year" type="number" defaultValue={new Date().getFullYear()} /><input name="allocated_days" type="number" min="0" max="365" required /><input name="reason" required placeholder={ar ? "سبب التعديل" : "Adjustment reason"} /><button type="submit">{ar ? "حفظ الرصيد" : "Save balance"}</button></form></details>}
          <ul className="operation-list">{leaveRequests.map((item) => <li key={item.id}><div><strong>{employeeName(employees, item.membership_id)}</strong><span>{item.starts_on}–{item.ends_on} · {item.days} {ar ? "يوم" : "days"} · {statusLabel(item.status, ar)}</span><small>{item.reason}</small></div>{canManage && item.status === "pending" && <div className="button-row"><form action={reviewLeaveAction.bind(null, locale, item.id, "approved")}><button type="submit">{ar ? "قبول" : "Approve"}</button></form><form action={reviewLeaveAction.bind(null, locale, item.id, "rejected")}><button type="submit" className="danger-button">{ar ? "رفض" : "Reject"}</button></form></div>}</li>)}</ul>
        </div>
      </section>

      <section className="portal-section" aria-labelledby="documents-title">
        <h2 id="documents-title">{ar ? "وثائق الموظفين" : "Employee documents"}</h2>
        <FileUploadForm locale={locale} />
        <form action={documentAction} className="portal-form operation-form">
          {canManage && <select name="membership_id"><option value="">{ar ? "الموظف الحالي" : "Current user"}</option>{employees.map((employee) => <option key={employee.membership_id} value={employee.membership_id}>{employee.display_name}</option>)}</select>}
          <select name="document_type">{documentTypes.map((type) => <option key={type} value={type}>{documentTypeLabel(type, ar)}</option>)}</select>
          <input name="document_number" placeholder={ar ? "رقم الوثيقة" : "Document number"} /><input name="issued_on" type="date" /><input name="expires_on" type="date" /><input name="attachment_file_id" required placeholder={ar ? "معرف الملف المرفوع" : "Uploaded file ID"} /><input name="reminder_days" type="number" defaultValue="30" min="0" max="365" /><button type="submit">{ar ? "حفظ الوثيقة" : "Save document"}</button>
        </form>
        <ul className="operation-list">
          {documents.map((item) => (
            <li key={item.id}>
              <div>
                <strong>{employeeName(employees, item.membership_id)} · {item.custom_type_name || documentTypeLabel(item.document_type, ar)}</strong>
                <span>{item.document_number || "—"} · {item.issued_on || "—"} → {item.expires_on || "—"}</span>
                <span className="status-pill">{statusLabel(item.status, ar)} · {statusLabel(item.review_status, ar)}</span>
                <a className="language-link" href={`/api/files/${item.attachment_file_id}`}>{ar ? "تنزيل الملف" : "Download file"}</a>
                <details>
                  <summary>{ar ? "تفاصيل وتعديل الوثيقة" : "Document details and edit"}</summary>
                  <form action={updateDocumentAction.bind(null, locale, item.id)} className="portal-form operation-form">
                    <input type="hidden" name="version" value={item.version} />
                    <select name="document_type" defaultValue={item.document_type}>{documentTypes.map((type) => <option key={type} value={type}>{documentTypeLabel(type, ar)}</option>)}</select>
                    <input name="custom_type_name" defaultValue={item.custom_type_name ?? ""} placeholder={ar ? "اسم النوع المخصص" : "Custom type name"} />
                    <input name="document_number" defaultValue={item.document_number ?? ""} placeholder={ar ? "رقم الوثيقة" : "Document number"} />
                    <input name="issued_on" type="date" defaultValue={item.issued_on ?? ""} />
                    <input name="expires_on" type="date" defaultValue={item.expires_on ?? ""} />
                    <input name="attachment_file_id" defaultValue={item.attachment_file_id} required />
                    <input name="reminder_days" type="number" min="0" max="365" defaultValue={item.reminder_days} />
                    <button type="submit">{ar ? "حفظ التعديل" : "Save changes"}</button>
                  </form>
                </details>
              </div>
              <div className="button-row">
                {canManage && item.review_status === "pending_review" && <><form action={reviewDocumentAction.bind(null, locale, item.id, "valid")}><button type="submit">{ar ? "اعتماد" : "Validate"}</button></form><form action={reviewDocumentAction.bind(null, locale, item.id, "rejected")}><button type="submit" className="danger-button">{ar ? "رفض" : "Reject"}</button></form></>}
                <form action={deleteDocumentAction.bind(null, locale, item.id, item.version)}><button type="submit" className="danger-button">{ar ? "حذف" : "Delete"}</button></form>
              </div>
            </li>
          ))}
        </ul>
      </section>

      {canManage && (
        <section className="portal-section split-sections">
          <div>
            <h2>{ar ? "التقارير والتصدير" : "Reports and exports"}</h2>
            <form action={exportAction} className="portal-form operation-form">
              <select name="report_type" defaultValue="attendance">
                {reportExportTypes.map((type) => (
                  <option key={type} value={type}>{reportTypeLabel(type, ar)}</option>
                ))}
              </select>
              <select name="report_types" multiple size={3} aria-label={ar ? "أنواع إضافية في الملف نفسه" : "Additional report types in the same file"}>
                {reportExportTypes.map((type) => (
                  <option key={type} value={type}>{ar ? `إضافة: ${reportTypeLabel(type, true)}` : `Also include: ${reportTypeLabel(type, false)}`}</option>
                ))}
              </select>
              <select name="membership_id" defaultValue="" aria-label={ar ? "الموظف" : "Employee"}>
                <option value="">{ar ? "كل الموظفين" : "All employees"}</option>
                {employees.map((employee) => (
                  <option key={employee.membership_id} value={employee.membership_id}>{employee.display_name}</option>
                ))}
              </select>
              <select name="export_format" defaultValue="pdf">
                <option value="pdf">PDF</option>
                <option value="xlsx">Excel/XLSX</option>
              </select>
              <input name="date_from" type="date" aria-label={ar ? "من تاريخ" : "From date"} />
              <input name="date_to" type="date" aria-label={ar ? "إلى تاريخ" : "To date"} />
              <button type="submit">{ar ? "إنشاء التصدير" : "Create export"}</button>
            </form>
            <ul className="operation-list">
              {exports.map((job) => (
                <li key={job.id}>
                  <div>
                    <strong>{reportTypeLabel(job.report_type, ar)} · {job.export_format === "xlsx" ? "Excel" : "PDF"}</strong>
                    <span>{statusLabel(job.status, ar)} · {job.progress_percent}%</span>
                    <small>{ar ? "تاريخ إنشاء الملف" : "File generated"}: {exportDate(job.created_at, locale)} · {exportPeriod(job, ar)}</small>
                  </div>
                  {job.status === "completed" && (
                    <a className="language-link" href={`/${locale}/exports/${job.id}`}>{ar ? "تنزيل" : "Download"}</a>
                  )}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h2>{ar ? "الاشتراك" : "Subscription"}</h2>
            {subscription ? (
              <article className="subscription-card">
                <span className="status-pill">{statusLabel(subscription.status, ar)}</span>
                <h3>{subscription.plan.name}</h3>
                <p>{subscription.plan.code} · {billingCycleLabel(subscription.billing_cycle, ar)}</p>
                <p>{ar ? "ينتهي" : "Ends"}: {formatDate(subscription.ends_at, locale)}</p>
                <dl className="subscription-limits">
                  {Object.entries({ ...subscription.plan.limits, ...(subscription.limits_override ?? {}) }).map(([key, value]) => (
                    <div key={key}>
                      <dt>{subscriptionLimitLabel(key, ar)}</dt>
                      <dd>{formatLimitValue(key, value, ar)}</dd>
                    </div>
                  ))}
                </dl>
              </article>
            ) : (
              <p className="empty-state">{ar ? "لا يوجد اشتراك فعال." : "No active subscription."}</p>
            )}
          </div>
        </section>
      )}
      {canManage && (
        <section className="portal-section" aria-labelledby="report-center-title">
          <div className="section-heading">
            <div><h2 id="report-center-title">{ar ? "مركز التقارير" : "Report center"}</h2><p>{ar ? "تطبق الفلاتر على التقارير والترتيب." : "Filters apply to reports and attendance ranking."}</p></div>
            <a className="language-link" href={`/${locale}/company`}>{ar ? "مسح الفلاتر" : "Clear filters"}</a>
          </div>
          <form method="get" action={`/${locale}/company`} className="portal-form operation-form">
            <input name="report_date_from" type="date" defaultValue={reportFilters.date_from ?? ""} aria-label={ar ? "من تاريخ" : "From date"} />
            <input name="report_date_to" type="date" defaultValue={reportFilters.date_to ?? ""} aria-label={ar ? "إلى تاريخ" : "To date"} />
            <select name="report_membership_id" defaultValue={reportFilters.membership_id ?? ""}><option value="">{ar ? "كل الموظفين" : "All employees"}</option>{employees.map((item) => <option key={item.membership_id} value={item.membership_id}>{item.display_name}</option>)}</select>
            <select name="report_branch_id" defaultValue={reportFilters.branch_id ?? ""}><option value="">{ar ? "كل الفروع" : "All branches"}</option>{branches.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
            <select name="report_department_id" defaultValue={reportFilters.department_id ?? ""}><option value="">{ar ? "كل الأقسام" : "All departments"}</option>{departments.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
            <select name="report_group_id" defaultValue={reportFilters.group_id ?? ""}><option value="">{ar ? "كل المجموعات" : "All groups"}</option>{groups.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
            <input name="report_status" defaultValue={reportFilters.status ?? ""} placeholder={ar ? "الحالة (اختياري)" : "Status (optional)"} />
            <button type="submit">{ar ? "تطبيق الفلاتر" : "Apply filters"}</button>
          </form>
          <div className="metric-grid">
            {reportSections.map(({ key, label, report }) => (
              <details className="metric-card" key={key}>
                <summary><span>{label}</span><strong>{report.total}</strong></summary>
                <small>{Object.entries(report.status_counts).map(([itemStatus, count]) => `${statusLabel(itemStatus, ar)}: ${count}`).join(" · ") || (ar ? "لا توجد نتائج" : "No results")}</small>
                <ul className="operation-list">{report.items.slice(0, 10).map((item) => <li key={String(item.id)}><span>{String(item.title ?? item.document_type ?? item.request_type ?? item.starts_on ?? item.id)}</span><small>{statusLabel(String(item.status ?? ""), ar)}</small></li>)}</ul>
              </details>
            ))}
          </div>
          <div className="split-sections">
            <div><h3>{ar ? "ترتيب الحضور" : "Attendance ranking"}</h3><ol className="operation-list">{leaderboard.map((item) => <li key={`${item.rank}-${item.display_name}`}><strong>#{item.rank} {item.display_name}</strong><span>{item.on_time_days} {ar ? "أيام في الوقت" : "on-time days"} · {item.worked_minutes}m</span></li>)}</ol>{leaderboard.length === 0 && <p className="empty-state">{ar ? "الترتيب معطل أو لا توجد بيانات ضمن الفترة." : "Ranking is disabled or no data matches the period."}</p>}</div>
            <form action={leaderboardAction} className="portal-form operation-form">
              <h3>{ar ? "خصوصية الترتيب" : "Ranking privacy"}</h3>
              <label className="checkbox-field"><input type="checkbox" name="enabled" defaultChecked={leaderboardSettings.enabled} />{ar ? "تفعيل الترتيب" : "Enable ranking"}</label>
              <label className="checkbox-field"><input type="checkbox" name="anonymize" defaultChecked={leaderboardSettings.anonymize} />{ar ? "إخفاء أسماء الموظفين" : "Anonymize employee names"}</label>
              <select name="visibility" defaultValue={leaderboardSettings.visibility}><option value="disabled">{ar ? "معطل" : "Disabled"}</option><option value="manager_only">{ar ? "الإدارة فقط" : "Managers only"}</option><option value="branch">{ar ? "نفس الفرع" : "Same branch"}</option><option value="company">{ar ? "كل الشركة" : "Whole company"}</option></select>
              <button type="submit">{ar ? "حفظ الخصوصية" : "Save privacy"}</button>
            </form>
          </div>
        </section>
      )}
    </>
  );
}
