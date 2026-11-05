import Link from "next/link";
import { redirect } from "next/navigation";
import { WhatsAppContact } from "@/components/whatsapp-contact";

import { authorizedApiFetch, getWebSession } from "@/lib/auth/server-session";
import { canEnterCompanyPortal, type PortalRole } from "@/lib/auth/permissions";

import {
  archiveBranchAction,
  archiveShiftAction,
  bulkArchiveBranchesAction,
  bulkArchiveShiftsAction,
  bulkDeactivateEmployeesAction,
  logoutAction,
} from "./actions";
import { BranchAssignmentForm, type BranchAssignment } from "./branch-assignment-form";
import { BranchForm } from "./branch-form";
import { BranchEditForm, type EditableBranch } from "./branch-edit-form";
import { CompanySettingsForm, type CompanySettings } from "./company-settings-form";
import { EmployeeForm, type EditableEmployee } from "./employee-form";
import { InvitationCodeAction, InvitationForm } from "./invitation-form";
import { GroupManagement, type EditableGroup } from "./group-management";
import { MemberAccessForm, type MemberAccess } from "./member-access-form";
import { ReportsDashboard } from "./reports-dashboard";
import {
  markAllNotificationsReadAction,
  reviewGeofenceExitAction,
  updateNotificationPreferencesAction,
} from "./operations-actions";
import { OperationsDashboard, type ReportFilters } from "./operations-dashboard";
import { ShiftAssignmentForm, type ShiftAssignment } from "./shift-assignment-form";
import { ShiftEditForm, type EditableShift } from "./shift-edit-form";
import { ShiftForm } from "./shift-form";
import { statusLabel } from "./display-labels";

type Invitation = {
  id: string;
  full_name: string;
  email: string;
  role_code: string;
  status: string;
};

type Branch = EditableBranch;

type Shift = EditableShift & {
  id: string;
  code: string;
  name: string;
  start_time: string;
  end_time: string;
  is_overnight: boolean;
  working_days: number[];
  grace_period_minutes: number;
  break_duration_minutes: number;
  effective_from: string;
  effective_to: string | null;
  recurrence: {
    location_policy?: string;
    periods?: { start_time?: string; end_time?: string }[];
  };
  is_active: boolean;
  version: number;
};

type NamedOption = { id: string; name: string };
type PermissionItem = { code: string; description: string };
type BranchSupervisorAssignment = {
  branch_id: string;
  membership_ids: string[];
  version: number;
};
type GeofenceExit = {
  id: string;
  membership_id: string;
  branch_id: string;
  status: string;
  detected_at: string;
  distance_m: number | null;
  accuracy_m: number | null;
  location_permission: string;
  consecutive_outside_samples: number;
  review_comment: string | null;
  version: number;
};
type Notification = {
  id: string;
  title: string;
  body: string;
  kind: string;
  deep_link: string;
  urgent: boolean;
  read_at: string | null;
  created_at: string;
};
type NotificationPreferences = {
  in_app_enabled: boolean;
  push_enabled: boolean;
  email_enabled: boolean;
  muted_kinds: string[];
  quiet_hours_start: string | null;
  quiet_hours_end: string | null;
};
type CompanyTab = "employees" | "branches" | "shifts" | "groups" | "operations" | "reports" | "notifications" | "geofence" | "admin";

export default async function CompanyPortal({
  params,
  searchParams,
}: {
  params: Promise<{ lang: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { lang } = await params;
  const query = await searchParams;
  const reportValue = (key: string) => {
    const value = query[`report_${key}`];
    return typeof value === "string" ? value : undefined;
  };
  const reportFilters: ReportFilters = {
    date_from: reportValue("date_from"),
    date_to: reportValue("date_to"),
    membership_id: reportValue("membership_id"),
    branch_id: reportValue("branch_id"),
    department_id: reportValue("department_id"),
    group_id: reportValue("group_id"),
    status: reportValue("status"),
  };
  const tabValue = query.tab;
  const requestedTab = typeof tabValue === "string" ? tabValue : undefined;
  const ar = lang === "ar";
  const session = await getWebSession();
  if (!session) redirect(`/${lang}/login`);
  if (!session.roles.some((role) => canEnterCompanyPortal(role as PortalRole))) {
    redirect(`/${lang}`);
  }

  const canManage = session.roles.some((role) =>
    ["OWNER", "MANAGER", "HR_OFFICER"].includes(role),
  );
  const canEditEmployees = canManage;
  const roles = session.roles ?? [];
  const sessionPermissions = session.permissions ?? [];
  const canManageSettings = roles.includes("OWNER");
  const canManageGroups = sessionPermissions.includes("departments:manage");
  const canManageBranches = sessionPermissions.includes("branches:manage");
  const canViewReports = canManage || sessionPermissions.includes("reports:view");
  const canReviewGeofence = sessionPermissions.includes("geofence_exits:manage");
  const [
    invitationResponse,
    employeeResponse,
    settingsResponse,
    branchResponse,
    shiftResponse,
    departmentResponse,
    groupResponse,
    permissionResponse,
    accessResponse,
    geofenceResponse,
    notificationsResponse,
    notificationPreferencesResponse,
    branchSupervisorsResponse,
    shiftAssignmentsResponse,
    taskRecipientsResponse,
    platformDashboardResponse,
  ] = await Promise.all([
    canManage ? authorizedApiFetch("/invitations") : Promise.resolve(null),
    authorizedApiFetch("/employees?page_size=100"),
    authorizedApiFetch("/companies/current"),
    authorizedApiFetch("/branches?page_size=100"),
    authorizedApiFetch("/shifts?page_size=100"),
    canManageSettings ? authorizedApiFetch("/departments") : Promise.resolve(null),
    canManageSettings || canManageGroups
      ? authorizedApiFetch("/groups?page_size=100&include_inactive=true")
      : Promise.resolve(null),
    canManageSettings ? authorizedApiFetch("/members/access-catalog") : Promise.resolve(null),
    canManageSettings ? authorizedApiFetch("/members/access") : Promise.resolve(null),
    canReviewGeofence
      ? authorizedApiFetch("/geofence-exit-events")
      : Promise.resolve(null),
    authorizedApiFetch("/notifications"),
    authorizedApiFetch("/notifications/preferences"),
    canManageBranches
      ? authorizedApiFetch("/branches/management/supervisors")
      : Promise.resolve(null),
    canEditEmployees ? authorizedApiFetch("/shifts/assignments") : Promise.resolve(null),
    authorizedApiFetch("/tasks/recipients"),
    canManageSettings ? authorizedApiFetch("/platform/dashboard") : Promise.resolve(null),
  ]);
  const invitationPayload: { items: Invitation[] } = invitationResponse?.ok
    ? ((await invitationResponse.json()) as { items: Invitation[] })
    : { items: [] };
  const employeePayload: { items: EditableEmployee[] } = employeeResponse.ok
    ? ((await employeeResponse.json()) as { items: EditableEmployee[] })
    : { items: [] };
  const settings = settingsResponse.ok
    ? ((await settingsResponse.json()) as CompanySettings)
    : null;
  const branchPayload: { items: Branch[] } = branchResponse.ok
    ? ((await branchResponse.json()) as { items: Branch[] })
    : { items: [] };
  const shiftPayload: { items: Shift[] } = shiftResponse.ok
    ? ((await shiftResponse.json()) as { items: Shift[] })
    : { items: [] };
  const departmentPayload: { items: NamedOption[] } = departmentResponse?.ok
    ? ((await departmentResponse.json()) as { items: NamedOption[] })
    : { items: [] };
  const groupPayload: { items: EditableGroup[] } = groupResponse?.ok
    ? ((await groupResponse.json()) as { items: EditableGroup[] })
    : { items: [] };
  const permissions: PermissionItem[] = permissionResponse?.ok
    ? ((await permissionResponse.json()) as PermissionItem[])
    : [];
  const accessItems: MemberAccess[] = accessResponse?.ok
    ? ((await accessResponse.json()) as MemberAccess[])
    : [];
  const geofenceEvents: GeofenceExit[] = geofenceResponse?.ok
    ? ((await geofenceResponse.json()) as GeofenceExit[])
    : [];
  const employeeNameById = new Map(employeePayload.items.map((item) => [item.membership_id, item.display_name]));
  const branchNameById = new Map(branchPayload.items.map((item) => [item.id, item.name]));
  const geofenceStatusLabel = (value: string) =>
    ar
      ? ({
          unauthorized: "مغادرة غير مصرح بها",
          confirmed_unauthorized: "مغادرة غير مصرح بها مؤكدة",
          approved_exception: "استثناء معتمد",
          dismissed: "مستبعدة",
          reconfirmed: "عاد إلى النطاق",
          observing: "تحت المراقبة",
        }[value] ?? statusLabel(value, true))
      : value.replaceAll("_", " ");
  const notificationTitle = (item: Notification) => {
    if (!ar) return item.title;
    return ({
      permission_requested: "طلب استئذان جديد",
      permission_approved: "تم اعتماد طلب الاستئذان",
      permission_rejected: "تم رفض طلب الاستئذان",
      leave_requested: "طلب إجازة جديد",
      leave_reviewed: "تمت مراجعة طلب الإجازة",
      geofence_exit_unauthorized: "مغادرة غير مصرح بها من النطاق",
      task_created: `مهمة جديدة: ${item.title}`,
      task_comment_added: `رسالة جديدة على المهمة: ${item.title}`,
      task_status_changed: `تحديث حالة المهمة: ${item.title}`,
      device_change_requested: "طلب تغيير جهاز جديد",
      missing_checkout: "تم إغلاق الوردية دون تسجيل الانصراف",
      attendance_reminder: "تذكير بإثبات الحضور",
      attendance_absent: "تم تسجيل الغياب",
    } as Record<string, string>)[item.kind] ?? item.title;
  };
  const notificationBody = (item: Notification) => {
    if (!ar) return item.body;
    return ({
      permission_requested: "أرسل أحد الموظفين طلب استئذان أو خروج مبكر للمراجعة.",
      permission_approved: "تمت الموافقة على طلب الاستئذان.",
      permission_rejected: "تم رفض طلب الاستئذان.",
      leave_requested: "أرسل أحد الموظفين طلب إجازة للمراجعة.",
      leave_reviewed: "تم تحديث حالة طلب الإجازة.",
      geofence_exit_unauthorized: "بقي موظف خارج نطاق الفرع دون استئذان معتمد.",
      task_created: "تم إسناد مهمة جديدة إليك.",
      task_comment_added: "أضاف أحد المشاركين رسالة جديدة إلى المهمة.",
      task_status_changed: "تم تحديث حالة المهمة.",
      device_change_requested: "طلب موظف اعتماد هاتف بديل للمراجعة.",
      missing_checkout: "انتهت الوردية دون تسجيل الانصراف، فأُغلقت تلقائياً بعد المهلة.",
      attendance_reminder: "لم يثبت الموظف حضوره بعد انتهاء فترة السماح.",
      attendance_absent: "انتهت الوردية دون تسجيل حضور، لذلك أُغلق اليوم كسجل غياب.",
    } as Record<string, string>)[item.kind] ?? item.body;
  };
  const notifications: Notification[] = notificationsResponse.ok
    ? ((await notificationsResponse.json()) as Notification[])
    : [];
  const notificationPreferences: NotificationPreferences = notificationPreferencesResponse.ok
    ? ((await notificationPreferencesResponse.json()) as NotificationPreferences)
    : {
        in_app_enabled: true,
        push_enabled: true,
        email_enabled: false,
        muted_kinds: [],
        quiet_hours_start: null,
        quiet_hours_end: null,
      };
  const branchSupervisorAssignments: BranchSupervisorAssignment[] = branchSupervisorsResponse?.ok
    ? ((await branchSupervisorsResponse.json()) as BranchSupervisorAssignment[])
    : [];
  const shiftAssignments: ShiftAssignment[] = shiftAssignmentsResponse?.ok
    ? ((await shiftAssignmentsResponse.json()) as ShiftAssignment[])
    : [];
  const taskRecipients: NamedOption[] = taskRecipientsResponse.ok
    ? ((await taskRecipientsResponse.json()) as NamedOption[])
    : [];
  const accessByMember = new Map(accessItems.map((item) => [item.membership_id, item]));
  const rolesFor = (employee: EditableEmployee) =>
    new Set([employee.role_code, ...(accessByMember.get(employee.membership_id)?.role_codes ?? [])]);
  const managerOptions = employeePayload.items
    .filter((employee) => {
      const roles = rolesFor(employee);
      return employee.membership_status === "active" && (roles.has("OWNER") || roles.has("MANAGER"));
    })
    .map((employee) => ({ id: employee.membership_id, name: employee.display_name }));
  const supervisorOptions = employeePayload.items
    .filter((employee) => employee.membership_status === "active" && rolesFor(employee).has("SUPERVISOR"))
    .map((employee) => ({ id: employee.membership_id, name: employee.display_name }));
  const deletableEmployees = employeePayload.items.filter(
    (employee) => employee.role_code !== "OWNER" && employee.membership_status !== "inactive",
  );
  const supervisorsByBranch = new Map(
    branchSupervisorAssignments.map((assignment) => [assignment.branch_id, assignment]),
  );
  const tabs: { key: CompanyTab; label: string; description: string }[] = [
    {
      key: "employees",
      label: ar ? "الموظفون" : "Employees",
      description: ar ? "ملفات وصلاحيات" : "Profiles and access",
    },
    {
      key: "branches",
      label: ar ? "الفروع" : "Branches",
      description: ar ? "فروع وتعيينات" : "Sites and assignments",
    },
    {
      key: "shifts",
      label: ar ? "الورديات" : "Shifts",
      description: ar ? "جداول العمل" : "Schedules",
    },
    ...(canManageGroups
      ? [{
          key: "groups" as const,
          label: ar ? "المجموعات" : "Groups",
          description: ar ? "فرق تشغيلية" : "Operational teams",
        }]
      : []),
    {
      key: "operations",
      label: ar ? "العمليات" : "Operations",
      description: ar ? "حضور ومهام" : "Attendance and work",
    },
    ...(canViewReports
      ? [{
          key: "reports" as const,
          label: ar ? "التقارير" : "Reports",
          description: ar ? "PDF و Excel" : "PDF and Excel",
        }]
      : []),
    {
      key: "notifications",
      label: ar ? "الإشعارات" : "Notifications",
      description: ar ? "تنبيهات" : "Alerts",
    },
    ...(canReviewGeofence
      ? [{
          key: "geofence" as const,
          label: ar ? "النطاق" : "Geofence",
          description: ar ? "مراجعة المغادرة" : "Exit review",
        }]
      : []),
    ...(canManage || canManageSettings
      ? [{
          key: "admin" as const,
          label: ar ? "الإدارة" : "Admin",
          description: ar ? "دعوات وإعدادات" : "Invites and settings",
        }]
      : []),
  ];
  const activeTab = tabs.some((tab) => tab.key === requestedTab)
    ? requestedTab as CompanyTab
    : "employees";
  const assignmentEntries =
    (activeTab === "branches" || activeTab === "employees") && canEditEmployees
      ? await Promise.all(
          employeePayload.items
            .filter((employee) => employee.role_code !== "OWNER")
            .map(async (employee) => {
              const response = await authorizedApiFetch(`/branches/assignments/${employee.membership_id}`);
              const assignments = response.ok
                ? ((await response.json()) as BranchAssignment[])
                : [];
              return [employee.membership_id, assignments] as const;
            }),
        )
      : [];
  const assignmentsByMember = Object.fromEntries(assignmentEntries);
  const currentShiftByMember = new Map(
    shiftAssignments
      .filter((assignment) => assignment.membership_id && assignment.effective_to === null)
      .map((assignment) => [assignment.membership_id!, assignment]),
  );
  const signOut = logoutAction.bind(null, lang);
  const otherLang = ar ? "en" : "ar";
  const isPlatformAdmin = platformDashboardResponse?.ok === true;

  return (
    <main className="portal-shell">
      <section className="portal-card wide">
        <header className="portal-header">
          <div>
            <p className="foundation-eyebrow">DawamTech | دوام تك</p>
            <h1>{session.company.display_name}</h1>
            <p>{session.user.full_name} · {session.roles.join(", ")}</p>
          </div>
          <form action={signOut}>
            <button type="submit">{ar ? "تسجيل الخروج" : "Sign out"}</button>
          </form>
          <div className="portal-header-links">
            <WhatsAppContact lang={lang} />
            <Link className="language-link secondary" href={`/${lang}/subscription`}>
              {ar ? "الاشتراكات" : "Subscriptions"}
            </Link>
            {isPlatformAdmin && (
              <Link className="language-link" href={`/${lang}/platform`}>
                {ar ? "لوحة مالك التطبيق" : "Platform owner"}
              </Link>
            )}
          </div>
          <Link className="language-link" href={`/${otherLang}/company?tab=${activeTab}`}>
            {ar ? "English" : "العربية"}
          </Link>
        </header>
        <nav className="portal-tabs" aria-label={ar ? "أقسام الشركة" : "Company sections"}>
          {tabs.map((tab) => (
            <Link
              aria-current={activeTab === tab.key ? "page" : undefined}
              className={activeTab === tab.key ? "portal-tab active" : "portal-tab"}
              href={`/${lang}/company?tab=${tab.key}`}
              key={tab.key}
            >
              <span>{tab.label}</span>
              <small>{tab.description}</small>
            </Link>
          ))}
        </nav>
        {activeTab === "employees" && <section className="portal-section">
          <h2>{ar ? "الموظفون" : "Employees"}</h2>
          <p>{ar ? "ملفات الموظفين ضمن شركتك فقط." : "Employee profiles scoped to your company."}</p>
          {employeePayload.items.length === 0 ? (
            <p>{ar ? "لا توجد ملفات موظفين." : "No employee profiles found."}</p>
          ) : canEditEmployees ? (
            <>
              {deletableEmployees.length > 0 && (
                <form action={bulkDeactivateEmployeesAction.bind(null, lang)} className="bulk-delete-panel">
                  <strong>{ar ? "حذف جماعي للموظفين" : "Bulk delete employees"}</strong>
                  <p>{ar ? "يتم تعطيل العضوية وسحب الأجهزة والجلسات، مع بقاء السجلات التاريخية." : "This deactivates memberships and revokes devices/sessions while preserving history."}</p>
                  <div className="bulk-delete-grid">
                    {deletableEmployees.map((employee) => (
                      <label key={employee.membership_id}>
                        <input name="targets" type="checkbox" value={`${employee.membership_id}:${employee.membership_version}`} />
                        <span>{employee.display_name}</span>
                      </label>
                    ))}
                  </div>
                  <button type="submit" className="danger-button">{ar ? "حذف المحدد" : "Delete selected"}</button>
                </form>
              )}
              <div className="employee-list">
                {employeePayload.items.map((employee) => (
                  <div key={employee.membership_id}>
                    <EmployeeForm
                      employee={employee}
                      locale={lang}
                      branches={branchPayload.items}
                      shifts={shiftPayload.items}
                      currentBranchAssignment={(assignmentsByMember[employee.membership_id] ?? []).find((assignment) => assignment.effective_to === null) ?? null}
                      currentShiftAssignment={currentShiftByMember.get(employee.membership_id) ?? null}
                    />
                    {canManageSettings && employee.role_code !== "OWNER" && accessByMember.has(employee.membership_id) && (
                      <MemberAccessForm
                        locale={lang}
                        member={accessByMember.get(employee.membership_id)!}
                        permissions={permissions}
                        branches={branchPayload.items}
                        departments={departmentPayload.items}
                        groups={groupPayload.items}
                      />
                    )}
                  </div>
                ))}
              </div>
            </>
          ) : (
            <ul className="invitation-list">
              {employeePayload.items.map((employee) => (
                <li key={employee.membership_id}>
                  <strong>{employee.display_name}</strong>
                  <span>{employee.email}</span>
                  <span>{employee.job_title || employee.role_code}</span>
                </li>
              ))}
            </ul>
          )}
        </section>}
        {activeTab === "branches" && <section className="portal-section">
          <h2>{ar ? "الفروع" : "Branches"}</h2>
          <p>{ar ? "الموقع ونطاق الحضور محفوظان في الخادم." : "Location and attendance radius are stored by the server."}</p>
          {canEditEmployees && <BranchForm locale={lang} />}
          {canEditEmployees && (
            <BranchAssignmentForm
              locale={lang}
              employees={employeePayload.items}
              branches={branchPayload.items}
              assignmentsByMember={assignmentsByMember}
            />
          )}
          {branchPayload.items.length === 0 ? (
            <p>{ar ? "لا توجد فروع نشطة." : "No active branches."}</p>
          ) : (
            <>
              {canEditEmployees && (
                <form action={bulkArchiveBranchesAction.bind(null, lang)} className="bulk-delete-panel">
                  <strong>{ar ? "حذف جماعي للفروع" : "Bulk delete branches"}</strong>
                  <p>{ar ? "يتم أرشفة الفروع المحددة وإخفاؤها من القوائم النشطة." : "Selected branches are archived and removed from active lists."}</p>
                  <div className="bulk-delete-grid">
                    {branchPayload.items.map((branch) => (
                      <label key={branch.id}>
                        <input name="targets" type="checkbox" value={`${branch.id}:${branch.version}`} />
                        <span>{branch.name}</span>
                      </label>
                    ))}
                  </div>
                  <button type="submit" className="danger-button">{ar ? "حذف المحدد" : "Delete selected"}</button>
                </form>
              )}
              <ul className="branch-list">
                {branchPayload.items.map((branch) => {
                  const archive = archiveBranchAction.bind(null, lang, branch.id, branch.version);
                  return (
                    <li key={branch.id}>
                      <div><strong>{branch.name}</strong><span>{branch.code} · {branch.saudi_short_address || branch.full_address}</span></div>
                      <span>{branch.latitude}, {branch.longitude} · {branch.geofence_radius_m}m</span>
                      {canManageBranches && (
                        <BranchEditForm
                          locale={lang}
                          branch={branch}
                          managerOptions={managerOptions}
                          supervisorOptions={supervisorOptions}
                          supervisorIds={supervisorsByBranch.get(branch.id)?.membership_ids ?? []}
                          supervisorVersion={supervisorsByBranch.get(branch.id)?.version ?? branch.version}
                        />
                      )}
                      {canEditEmployees && <form action={archive}><button className="danger-button" type="submit">{ar ? "حذف" : "Delete"}</button></form>}
                    </li>
                  );
                })}
              </ul>
            </>
          )}
        </section>}
        {activeTab === "shifts" && <section className="portal-section">
          <h2>{ar ? "الورديات" : "Shifts"}</h2>
          <p>{ar ? "يحسب الخادم الورديات الليلية وتعارضات التعيين." : "The server calculates overnight shifts and assignment conflicts."}</p>
          {canEditEmployees && <ShiftForm locale={lang} />}
          {canEditEmployees && (
            <ShiftAssignmentForm
              locale={lang}
              shifts={shiftPayload.items}
              employees={employeePayload.items}
              branches={branchPayload.items}
              assignments={shiftAssignments}
            />
          )}
          {shiftPayload.items.length === 0 ? (
            <p>{ar ? "لا توجد ورديات نشطة." : "No active shifts."}</p>
          ) : (
            <>
              {canEditEmployees && (
                <form action={bulkArchiveShiftsAction.bind(null, lang)} className="bulk-delete-panel">
                  <strong>{ar ? "حذف جماعي للورديات" : "Bulk delete shifts"}</strong>
                  <p>{ar ? "يتم أرشفة الورديات المحددة وإيقاف استخدامها في التعيينات الجديدة." : "Selected shifts are archived and stopped for new active use."}</p>
                  <div className="bulk-delete-grid">
                    {shiftPayload.items.map((shift) => (
                      <label key={shift.id}>
                        <input name="targets" type="checkbox" value={`${shift.id}:${shift.version}`} />
                        <span>{shift.name}</span>
                      </label>
                    ))}
                  </div>
                  <button type="submit" className="danger-button">{ar ? "حذف المحدد" : "Delete selected"}</button>
                </form>
              )}
              <ul className="branch-list">
                {shiftPayload.items.map((shift) => {
                  const archive = archiveShiftAction.bind(null, lang, shift.id, shift.version);
                  const periods = shift.recurrence?.periods ?? [];
                  const secondPeriod = periods[1];
                  const locationless = shift.recurrence?.location_policy === "location_not_required";
                  return (
                    <li key={shift.id}>
                      <div>
                        <strong>{shift.name}</strong>
                        <span>
                          {shift.code} · {shift.start_time.slice(0, 5)}–{shift.end_time.slice(0, 5)}
                          {secondPeriod?.start_time && secondPeriod?.end_time ? ` · ${secondPeriod.start_time.slice(0, 5)}–${secondPeriod.end_time.slice(0, 5)}` : ""}
                        </span>
                      </div>
                      <span>
                        {shift.is_overnight ? (ar ? "ليلية" : "Overnight") : (ar ? "نهارية" : "Same day")} · {shift.working_days.length} {ar ? "أيام" : "days"}
                        {locationless ? ` · ${ar ? "بدون شرط موقع" : "No location required"}` : ""}
                      </span>
                      {canEditEmployees && <ShiftEditForm locale={lang} shift={shift} />}
                      {canEditEmployees && <form action={archive}><button className="danger-button" type="submit">{ar ? "حذف" : "Delete"}</button></form>}
                    </li>
                  );
                })}
              </ul>
            </>
          )}
        </section>}
        {activeTab === "groups" && canManageGroups && (
          <GroupManagement
            locale={lang}
            groups={groupPayload.items}
            employees={employeePayload.items}
          />
        )}
        {activeTab === "operations" && <OperationsDashboard
          locale={lang}
          canManage={canManage}
          employees={employeePayload.items}
          taskRecipients={taskRecipients}
          branches={branchPayload.items}
          shifts={shiftPayload.items}
          departments={departmentPayload.items}
          groups={groupPayload.items}
          reportFilters={reportFilters}
        />}
        {activeTab === "reports" && canViewReports && <ReportsDashboard
          locale={lang}
          employees={employeePayload.items}
          branches={branchPayload.items}
          departments={departmentPayload.items}
          groups={groupPayload.items}
          reportFilters={reportFilters}
        />}
        {activeTab === "notifications" && <section className="portal-section">
          <div className="portal-header">
            <div>
              <h2>{ar ? "الإشعارات" : "Notifications"}</h2>
              <p>{ar ? "تنبيهات العمل وروابطها المباشرة." : "Work alerts with authorized deep links."}</p>
            </div>
            {notifications.some((item) => item.read_at === null) && (
              <form action={markAllNotificationsReadAction.bind(null, lang)}>
                <button type="submit">{ar ? "قراءة الكل" : "Read all"}</button>
              </form>
            )}
          </div>
          <details className="operation-form-card">
            <summary>{ar ? "تفضيلات الإشعارات" : "Notification preferences"}</summary>
            <form action={updateNotificationPreferencesAction.bind(null, lang)} className="portal-form operation-form">
              <label className="checkbox-field"><input type="checkbox" name="in_app_enabled" defaultChecked={notificationPreferences.in_app_enabled} />{ar ? "داخل التطبيق" : "In-app"}</label>
              <label className="checkbox-field"><input type="checkbox" name="push_enabled" defaultChecked={notificationPreferences.push_enabled} />{ar ? "إشعارات فورية" : "Push"}</label>
              <label className="checkbox-field"><input type="checkbox" name="email_enabled" defaultChecked={notificationPreferences.email_enabled} />{ar ? "بريد إلكتروني" : "Email"}</label>
              <input name="muted_kinds" defaultValue={notificationPreferences.muted_kinds.join(", ")} placeholder={ar ? "أنواع مكتومة مفصولة بفاصلة" : "Muted kinds, comma-separated"} />
              <input name="quiet_hours_start" type="time" defaultValue={notificationPreferences.quiet_hours_start ?? ""} />
              <input name="quiet_hours_end" type="time" defaultValue={notificationPreferences.quiet_hours_end ?? ""} />
              <button type="submit">{ar ? "حفظ التفضيلات" : "Save preferences"}</button>
            </form>
          </details>
          {notifications.length === 0 ? (
            <p>{ar ? "لا توجد إشعارات بعد." : "No notifications yet."}</p>
          ) : (
            <ul className="invitation-list">
              {notifications.map((item) => (
                <li key={item.id}>
                  <strong>{item.urgent ? "! " : ""}{notificationTitle(item)}</strong>
                  <span>{notificationBody(item)}</span>
                  <span>{new Date(item.created_at).toLocaleString(lang)}</span>
                </li>
              ))}
            </ul>
          )}
        </section>}
        {activeTab === "geofence" && canReviewGeofence && (
          <section className="portal-section">
            <h2>{ar ? "مراجعة مغادرة النطاق" : "Geofence exit review"}</h2>
            <p>
              {ar
                ? "تُعرض محاولات المغادرة المكتشفة آلياً ضمن نطاق صلاحياتك."
                : "Automatically detected exits within your assigned scope."}
            </p>
            {geofenceEvents.length === 0 ? (
              <p>{ar ? "لا توجد أحداث للمراجعة." : "No exit events to review."}</p>
            ) : (
              <ul className="branch-list">
                {geofenceEvents.map((event) => (
                  <li key={event.id}>
                    <div>
                      <strong>{geofenceStatusLabel(event.status)}</strong>
                      <span>
                        {new Date(event.detected_at).toLocaleString(lang)} · {event.distance_m ?? "—"}{ar ? "م" : "m"} · {event.consecutive_outside_samples} {ar ? "قراءات" : "samples"}
                      </span>
                      <span>
                        {ar ? "الموظف" : "Employee"}: {employeeNameById.get(event.membership_id) ?? event.membership_id}
                      </span>
                      <span>
                        {ar ? "الفرع" : "Branch"}: {branchNameById.get(event.branch_id) ?? event.branch_id}
                      </span>
                    </div>
                    {event.review_comment ? (
                      <span>{event.review_comment}</span>
                    ) : (
                      <div className="action-grid">
                        {(["confirmed_unauthorized", "dismissed", "approved_exception"] as const).map((decision) => {
                          const review = reviewGeofenceExitAction.bind(
                            null,
                            lang,
                            event.id,
                            event.version,
                            decision,
                          );
                          return (
                            <form action={review} key={decision}>
                              <input
                                name="comment"
                                required
                                minLength={3}
                                maxLength={2000}
                                placeholder={ar ? "سبب القرار" : "Decision reason"}
                              />
                              <button type="submit">{ar ? ({
                                confirmed_unauthorized: "تأكيد المخالفة",
                                dismissed: "استبعاد",
                                approved_exception: "اعتماد استثناء",
                              }[decision] ?? decision) : decision.replaceAll("_", " ")}</button>
                            </form>
                          );
                        })}
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </section>
        )}
        {activeTab === "admin" && (canManage || canManageSettings) && <>
        {canManage ? (
          <section className="portal-section">
            <h2>{ar ? "دعوات الموظفين" : "Employee invitations"}</h2>
            <InvitationForm locale={lang} />
            {invitationPayload.items.length === 0 ? (
              <p>{ar ? "لا توجد دعوات بعد." : "No invitations yet."}</p>
            ) : (
              <ul className="invitation-list admin-invitation-list">
                {invitationPayload.items.map((item) => (
                  <li key={item.id}>
                    <strong>{item.full_name}</strong>
                    <span>{item.email}</span>
                    <span>{item.role_code} · {item.status}</span>
                    <InvitationCodeAction locale={lang} invitationId={item.id} status={item.status} />
                  </li>
                ))}
              </ul>
            )}
          </section>
        ) : (
          <p>{ar ? "ليست لديك صلاحية لإدارة الدعوات." : "You cannot manage invitations."}</p>
        )}
        {canManageSettings && settings && (
          <section className="portal-section">
            <h2>{ar ? "إعدادات الشركة" : "Company settings"}</h2>
            <div className="company-identity-card" aria-label={ar ? "بيانات الشركة المحفوظة" : "Saved company identity"}>
              <div className="company-identity-copy">
                <strong>{settings.display_name}</strong>
                <span>{ar ? "البيانات المحفوظة وتظهر في التقارير" : "Saved details used in reports"}</span>
                <dl>
                  {settings.commercial_registration_number && <><dt>{ar ? "السجل التجاري" : "Commercial registration"}</dt><dd>{settings.commercial_registration_number}</dd></>}
                  {settings.unified_number && <><dt>{ar ? "الرقم الموحد" : "Unified number"}</dt><dd>{settings.unified_number}</dd></>}
                  {settings.contact_phone && <><dt>{ar ? "جوال الشركة" : "Company phone"}</dt><dd>{settings.contact_phone}</dd></>}
                  {settings.tax_number && <><dt>{ar ? "الرقم الضريبي" : "Tax number"}</dt><dd>{settings.tax_number}</dd></>}
                </dl>
              </div>
              {settings.logo_file_id ? (
                <img className="company-logo-preview company-logo-summary" src={`/api/files/${settings.logo_file_id}`} alt={ar ? "شعار الشركة" : "Company logo"} />
              ) : (
                <div className="company-logo-placeholder" aria-hidden="true">{ar ? "بدون شعار" : "No logo"}</div>
              )}
            </div>
            <CompanySettingsForm settings={settings} locale={lang} />
          </section>
        )}
        </>}
      </section>
    </main>
  );
}
