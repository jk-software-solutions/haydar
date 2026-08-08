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
  updateTaskStatusAction,
} from "./operations-actions";
import { QrTokenForm } from "./qr-token-form";
import { FileUploadForm } from "./file-upload-form";
import { authorizedApiFetch } from "@/lib/auth/server-session";

type Employee = { membership_id: string; display_name: string; role_code: string };
type Branch = { id: string; name: string };
type Shift = { id: string; name: string };
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
  work_date: string;
  status: string;
  checked_in_at: string | null;
  checked_out_at: string | null;
  worked_minutes: number;
  late_minutes: number;
  is_manual: boolean;
};
type Task = {
  id: string;
  title: string;
  priority: string;
  status: string;
  due_at: string | null;
  assignee_ids: string[];
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
};
type Subscription = {
  status: string;
  billing_cycle: string;
  ends_at: string;
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

export async function OperationsDashboard({
  locale,
  canManage,
  employees,
  branches,
  shifts,
}: {
  locale: string;
  canManage: boolean;
  employees: Employee[];
  branches: Branch[];
  shifts: Shift[];
}) {
  const ar = locale === "ar";
  const [overview, attendance, tasks, permissions, leaveTypes, leaveRequests, documents, exports, subscription] =
    await Promise.all([
      canManage ? jsonOr<Overview | null>("/reports/overview", null) : Promise.resolve(null),
      jsonOr<Attendance[]>(canManage ? "/attendance" : "/attendance/me", []),
      jsonOr<Task[]>(canManage ? "/tasks" : "/tasks?mine=true", []),
      jsonOr<PermissionRequest[]>(canManage ? "/permission-requests" : "/permission-requests?mine=true", []),
      jsonOr<LeaveType[]>("/leave/types", []),
      jsonOr<LeaveRequest[]>(canManage ? "/leave/requests" : "/leave/requests?mine=true", []),
      jsonOr<Document[]>("/documents", []),
      canManage ? jsonOr<ExportJob[]>("/reports/exports", []) : Promise.resolve([]),
      jsonOr<Subscription | null>("/billing/subscription", null),
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
            <thead><tr><th>{ar ? "الموظف" : "Employee"}</th><th>{ar ? "التاريخ" : "Date"}</th><th>{ar ? "الحالة" : "Status"}</th><th>{ar ? "العمل" : "Worked"}</th><th>{ar ? "التأخير" : "Late"}</th></tr></thead>
            <tbody>{attendance.slice(0, 50).map((item) => <tr key={item.id}><td>{employeeName(employees, item.membership_id)}</td><td>{formatDate(item.work_date, locale)}</td><td><span className="status-pill">{item.status}</span>{item.is_manual ? " · Manual" : ""}</td><td>{item.worked_minutes}m</td><td>{item.late_minutes}m</td></tr>)}</tbody>
          </table>
          {attendance.length === 0 && <p className="empty-state">{ar ? "لا توجد سجلات حضور بعد." : "No attendance records yet."}</p>}
        </div>
      </section>

      <section className="portal-section" aria-labelledby="tasks-title">
        <div className="section-heading"><h2 id="tasks-title">{ar ? "المهام" : "Tasks"}</h2><span className="status-pill">{tasks.length}</span></div>
        {canManage && (
          <form action={taskAction} className="portal-form operation-form">
            <input name="title" required placeholder={ar ? "عنوان المهمة" : "Task title"} />
            <textarea name="description" required placeholder={ar ? "الوصف" : "Description"} />
            <select name="priority" defaultValue="normal"><option value="low">Low</option><option value="normal">Normal</option><option value="high">High</option><option value="urgent">Urgent</option></select>
            <input name="due_at" type="datetime-local" aria-label={ar ? "موعد التسليم" : "Due date"} />
            <select name="membership_ids" required aria-label={ar ? "الموظف" : "Assignee"}><option value="">{ar ? "اختر الموظف" : "Select assignee"}</option>{employees.map((employee) => <option key={employee.membership_id} value={employee.membership_id}>{employee.display_name}</option>)}</select>
            <button type="submit">{ar ? "إنشاء المهمة" : "Create task"}</button>
          </form>
        )}
        <div className="kanban-grid">
          {tasks.map((task) => {
            const statusAction = updateTaskStatusAction.bind(null, locale, task.id, task.version);
            return (
              <article className="task-card" key={task.id}>
                <div className="section-heading"><strong>{task.title}</strong><span className={`status-pill ${task.priority === "urgent" ? "urgent" : ""}`}>{task.priority}</span></div>
                <p>{task.status} · {formatDate(task.due_at, locale)}</p>
                <small>{task.assignee_ids.map((id) => employeeName(employees, id)).join(", ")}</small>
                <form action={statusAction} className="inline-action">
                  <select name="status" defaultValue={task.status}><option value="viewed">Viewed</option><option value="in_progress">In progress</option><option value="completed">Completed</option><option value="needs_more_time">Needs more time</option><option value="blocked">Blocked</option><option value="postponed">Postponed</option></select>
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
            <select name="request_type" defaultValue="one_hour"><option value="one_hour">One hour</option><option value="multiple_hours">Multiple hours</option><option value="custom">Custom</option><option value="until_shift_end">Until shift end</option></select>
            <input name="starts_at" type="datetime-local" required />
            <input name="ends_at" type="datetime-local" required />
            <input name="reason" required placeholder={ar ? "السبب" : "Reason"} />
            <button type="submit">{ar ? "إرسال الطلب" : "Submit request"}</button>
          </form>
          <ul className="operation-list">{permissions.map((item) => <li key={item.id}><div><strong>{employeeName(employees, item.membership_id)}</strong><span>{item.request_type} · {item.status}</span><small>{item.reason}</small></div>{canManage && item.status === "pending" && <div className="button-row"><form action={reviewPermissionAction.bind(null, locale, item.id, "approved")}><button type="submit">{ar ? "قبول" : "Approve"}</button></form><form action={reviewPermissionAction.bind(null, locale, item.id, "rejected")}><button type="submit" className="danger-button">{ar ? "رفض" : "Reject"}</button></form></div>}</li>)}</ul>
        </div>
        <div>
          <h2>{ar ? "الإجازات" : "Leave"}</h2>
          <form action={leaveAction} className="portal-form operation-form">
            <select name="leave_type_id" required><option value="">{ar ? "نوع الإجازة" : "Leave type"}</option>{leaveTypes.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
            <input name="starts_on" type="date" required /><input name="ends_on" type="date" required />
            <input name="reason" required placeholder={ar ? "السبب" : "Reason"} /><button type="submit">{ar ? "إرسال الطلب" : "Submit request"}</button>
          </form>
          {canManage && <details className="operation-form-card"><summary>{ar ? "إعداد أنواع وأرصدة الإجازة" : "Configure leave types and balances"}</summary><form action={leaveTypeAction} className="portal-form inline"><input name="code" required placeholder="ANNUAL" /><input name="name" required placeholder={ar ? "إجازة سنوية" : "Annual leave"} /><input name="default_days" type="number" min="0" max="365" required /><label className="checkbox-field"><input name="is_paid" type="checkbox" defaultChecked />{ar ? "مدفوعة" : "Paid"}</label><button type="submit">{ar ? "إضافة النوع" : "Add type"}</button></form><form action={balanceAction} className="portal-form inline"><select name="membership_id" required><option value="">{ar ? "الموظف" : "Employee"}</option>{employees.map((employee) => <option key={employee.membership_id} value={employee.membership_id}>{employee.display_name}</option>)}</select><select name="leave_type_id" required><option value="">{ar ? "النوع" : "Type"}</option>{leaveTypes.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select><input name="year" type="number" defaultValue={new Date().getFullYear()} /><input name="allocated_days" type="number" min="0" max="365" required /><input name="reason" required placeholder={ar ? "سبب التعديل" : "Adjustment reason"} /><button type="submit">{ar ? "حفظ الرصيد" : "Save balance"}</button></form></details>}
          <ul className="operation-list">{leaveRequests.map((item) => <li key={item.id}><div><strong>{employeeName(employees, item.membership_id)}</strong><span>{item.starts_on}–{item.ends_on} · {item.days}d · {item.status}</span><small>{item.reason}</small></div>{canManage && item.status === "pending" && <div className="button-row"><form action={reviewLeaveAction.bind(null, locale, item.id, "approved")}><button type="submit">{ar ? "قبول" : "Approve"}</button></form><form action={reviewLeaveAction.bind(null, locale, item.id, "rejected")}><button type="submit" className="danger-button">{ar ? "رفض" : "Reject"}</button></form></div>}</li>)}</ul>
        </div>
      </section>

      <section className="portal-section" aria-labelledby="documents-title">
        <h2 id="documents-title">{ar ? "وثائق الموظفين" : "Employee documents"}</h2>
        <FileUploadForm locale={locale} />
        <form action={documentAction} className="portal-form operation-form">
          {canManage && <select name="membership_id"><option value="">{ar ? "الموظف الحالي" : "Current user"}</option>{employees.map((employee) => <option key={employee.membership_id} value={employee.membership_id}>{employee.display_name}</option>)}</select>}
          <select name="document_type"><option value="residency">Residency</option><option value="passport">Passport</option><option value="medical_insurance">Medical insurance</option><option value="employment_contract">Employment contract</option><option value="driving_license">Driving license</option><option value="vehicle_insurance">Vehicle insurance</option><option value="custom">Custom</option></select>
          <input name="document_number" placeholder={ar ? "رقم الوثيقة" : "Document number"} /><input name="issued_on" type="date" /><input name="expires_on" type="date" /><input name="attachment_file_id" required placeholder={ar ? "معرف الملف المرفوع" : "Uploaded file ID"} /><input name="reminder_days" type="number" defaultValue="30" min="0" max="365" /><button type="submit">{ar ? "حفظ الوثيقة" : "Save document"}</button>
        </form>
        <ul className="operation-list">
          {documents.map((item) => (
            <li key={item.id}>
              <div>
                <strong>{employeeName(employees, item.membership_id)} · {item.custom_type_name || item.document_type}</strong>
                <span>{item.document_number || "—"} · {item.issued_on || "—"} → {item.expires_on || "—"}</span>
                <span className="status-pill">{item.status} · {item.review_status}</span>
                <a className="language-link" href={`/api/files/${item.attachment_file_id}`}>{ar ? "تنزيل الملف" : "Download file"}</a>
                <details>
                  <summary>{ar ? "تفاصيل وتعديل الوثيقة" : "Document details and edit"}</summary>
                  <form action={updateDocumentAction.bind(null, locale, item.id)} className="portal-form operation-form">
                    <input type="hidden" name="version" value={item.version} />
                    <select name="document_type" defaultValue={item.document_type}><option value="residency">Residency</option><option value="passport">Passport</option><option value="medical_insurance">Medical insurance</option><option value="employment_contract">Employment contract</option><option value="driving_license">Driving license</option><option value="vehicle_insurance">Vehicle insurance</option><option value="custom">Custom</option></select>
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

      {canManage && <section className="portal-section split-sections"><div><h2>{ar ? "التقارير والتصدير" : "Reports and exports"}</h2><form action={exportAction} className="portal-form operation-form"><select name="report_type"><option value="attendance">Attendance</option><option value="geofence_exits">Unauthorized exits</option><option value="leave">Leave</option><option value="permissions">Permissions</option><option value="tasks">Tasks</option><option value="documents">Documents</option><option value="branches">Branches</option><option value="shifts">Shifts</option></select><select name="export_format"><option value="pdf">PDF</option><option value="xlsx">Excel/XLSX</option></select><input name="date_from" type="date" /><input name="date_to" type="date" /><button type="submit">{ar ? "إنشاء التصدير" : "Create export"}</button></form><ul className="operation-list">{exports.map((job) => <li key={job.id}><div><strong>{job.report_type} · {job.export_format.toUpperCase()}</strong><span>{job.status} · {job.progress_percent}%</span></div>{job.status === "completed" && <a className="language-link" href={`/api/exports/${job.id}`}>{ar ? "تنزيل" : "Download"}</a>}</li>)}</ul></div><div><h2>{ar ? "الاشتراك" : "Subscription"}</h2>{subscription ? <article className="subscription-card"><span className="status-pill">{subscription.status}</span><h3>{subscription.plan.name}</h3><p>{subscription.plan.code} · {subscription.billing_cycle}</p><p>{ar ? "ينتهي" : "Ends"}: {formatDate(subscription.ends_at, locale)}</p><pre>{JSON.stringify(subscription.plan.limits, null, 2)}</pre></article> : <p className="empty-state">{ar ? "لا يوجد اشتراك فعال." : "No active subscription."}</p>}</div></section>}
    </>
  );
}
