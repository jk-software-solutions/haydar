import { redirect } from "next/navigation";

import { authorizedApiFetch, getWebSession } from "@/lib/auth/server-session";
import { canEnterCompanyPortal, type PortalRole } from "@/lib/auth/permissions";

import { archiveBranchAction, archiveShiftAction, logoutAction } from "./actions";
import { BranchForm } from "./branch-form";
import { CompanySettingsForm, type CompanySettings } from "./company-settings-form";
import { EmployeeForm, type EditableEmployee } from "./employee-form";
import { InvitationForm } from "./invitation-form";
import { MemberAccessForm, type MemberAccess } from "./member-access-form";
import {
  markAllNotificationsReadAction,
  reviewGeofenceExitAction,
} from "./operations-actions";
import { OperationsDashboard } from "./operations-dashboard";
import { ShiftForm } from "./shift-form";

type Invitation = {
  id: string;
  full_name: string;
  email: string;
  role_code: string;
  status: string;
};

type Branch = {
  id: string;
  code: string;
  name: string;
  full_address: string;
  saudi_short_address: string | null;
  latitude: string;
  longitude: string;
  geofence_radius_m: number;
  timezone: string;
  version: number;
};

type Shift = {
  id: string;
  code: string;
  name: string;
  start_time: string;
  end_time: string;
  is_overnight: boolean;
  working_days: number[];
  grace_period_minutes: number;
  break_duration_minutes: number;
  version: number;
};

type NamedOption = { id: string; name: string };
type PermissionItem = { code: string; description: string };
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

export default async function CompanyPortal({
  params,
}: {
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;
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
  const canManageSettings = session.roles.includes("OWNER");
  const canReviewGeofence = session.permissions.includes("geofence_exits:manage");
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
  ] = await Promise.all([
    canManage ? authorizedApiFetch("/invitations") : Promise.resolve(null),
    authorizedApiFetch("/employees?page_size=100"),
    authorizedApiFetch("/companies/current"),
    authorizedApiFetch("/branches?page_size=100"),
    authorizedApiFetch("/shifts?page_size=100"),
    canManageSettings ? authorizedApiFetch("/departments") : Promise.resolve(null),
    canManageSettings ? authorizedApiFetch("/groups?page_size=100") : Promise.resolve(null),
    canManageSettings ? authorizedApiFetch("/members/access-catalog") : Promise.resolve(null),
    canManageSettings ? authorizedApiFetch("/members/access") : Promise.resolve(null),
    canReviewGeofence
      ? authorizedApiFetch("/geofence-exit-events")
      : Promise.resolve(null),
    authorizedApiFetch("/notifications"),
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
  const groupPayload: { items: NamedOption[] } = groupResponse?.ok
    ? ((await groupResponse.json()) as { items: NamedOption[] })
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
  const notifications: Notification[] = notificationsResponse.ok
    ? ((await notificationsResponse.json()) as Notification[])
    : [];
  const accessByMember = new Map(accessItems.map((item) => [item.membership_id, item]));
  const signOut = logoutAction.bind(null, lang);

  return (
    <main className="portal-shell">
      <section className="portal-card wide">
        <header className="portal-header">
          <div>
            <p className="foundation-eyebrow">HADIR | حاضر</p>
            <h1>{session.company.display_name}</h1>
            <p>{session.user.full_name} · {session.roles.join(", ")}</p>
          </div>
          <form action={signOut}>
            <button type="submit">{ar ? "تسجيل الخروج" : "Sign out"}</button>
          </form>
        </header>
        <section className="portal-section">
          <h2>{ar ? "الموظفون" : "Employees"}</h2>
          <p>{ar ? "ملفات الموظفين ضمن شركتك فقط." : "Employee profiles scoped to your company."}</p>
          {employeePayload.items.length === 0 ? (
            <p>{ar ? "لا توجد ملفات موظفين." : "No employee profiles found."}</p>
          ) : canEditEmployees ? (
            <div className="employee-list">
              {employeePayload.items.map((employee) => (
                <div key={employee.membership_id}>
                  <EmployeeForm employee={employee} locale={lang} />
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
        </section>
        <section className="portal-section">
          <h2>{ar ? "الفروع" : "Branches"}</h2>
          <p>{ar ? "الموقع ونطاق الحضور محفوظان في الخادم." : "Location and attendance radius are stored by the server."}</p>
          {canEditEmployees && <BranchForm locale={lang} />}
          {branchPayload.items.length === 0 ? (
            <p>{ar ? "لا توجد فروع نشطة." : "No active branches."}</p>
          ) : (
            <ul className="branch-list">
              {branchPayload.items.map((branch) => {
                const archive = archiveBranchAction.bind(null, lang, branch.id, branch.version);
                return (
                  <li key={branch.id}>
                    <div><strong>{branch.name}</strong><span>{branch.code} · {branch.saudi_short_address || branch.full_address}</span></div>
                    <span>{branch.latitude}, {branch.longitude} · {branch.geofence_radius_m}m</span>
                    {canEditEmployees && <form action={archive}><button className="danger-button" type="submit">{ar ? "أرشفة" : "Archive"}</button></form>}
                  </li>
                );
              })}
            </ul>
          )}
        </section>
        <section className="portal-section">
          <h2>{ar ? "الورديات" : "Shifts"}</h2>
          <p>{ar ? "يحسب الخادم الورديات الليلية وتعارضات التعيين." : "The server calculates overnight shifts and assignment conflicts."}</p>
          {canEditEmployees && <ShiftForm locale={lang} />}
          {shiftPayload.items.length === 0 ? (
            <p>{ar ? "لا توجد ورديات نشطة." : "No active shifts."}</p>
          ) : (
            <ul className="branch-list">
              {shiftPayload.items.map((shift) => {
                const archive = archiveShiftAction.bind(null, lang, shift.id, shift.version);
                return (
                  <li key={shift.id}>
                    <div><strong>{shift.name}</strong><span>{shift.code} · {shift.start_time.slice(0, 5)}–{shift.end_time.slice(0, 5)}</span></div>
                    <span>{shift.is_overnight ? (ar ? "ليلية" : "Overnight") : (ar ? "نهارية" : "Same day")} · {shift.working_days.length} {ar ? "أيام" : "days"}</span>
                    {canEditEmployees && <form action={archive}><button className="danger-button" type="submit">{ar ? "أرشفة" : "Archive"}</button></form>}
                  </li>
                );
              })}
            </ul>
          )}
        </section>
        <OperationsDashboard
          locale={lang}
          canManage={canManage}
          employees={employeePayload.items}
          branches={branchPayload.items}
          shifts={shiftPayload.items}
        />
        <section className="portal-section">
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
          {notifications.length === 0 ? (
            <p>{ar ? "لا توجد إشعارات بعد." : "No notifications yet."}</p>
          ) : (
            <ul className="invitation-list">
              {notifications.map((item) => (
                <li key={item.id}>
                  <strong>{item.urgent ? "! " : ""}{item.title}</strong>
                  <span>{item.body}</span>
                  <span>{new Date(item.created_at).toLocaleString(lang)}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
        {canReviewGeofence && (
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
                      <strong>{event.status}</strong>
                      <span>
                        {new Date(event.detected_at).toLocaleString(lang)} · {event.distance_m ?? "—"}m · {event.consecutive_outside_samples} samples
                      </span>
                      <span>
                        {ar ? "الموظف" : "Employee"}: {event.membership_id}
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
                              <button type="submit">{decision.replaceAll("_", " ")}</button>
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
        {canManage ? (
          <section className="portal-section">
            <h2>{ar ? "دعوات الموظفين" : "Employee invitations"}</h2>
            <InvitationForm locale={lang} />
            {invitationPayload.items.length === 0 ? (
              <p>{ar ? "لا توجد دعوات بعد." : "No invitations yet."}</p>
            ) : (
              <ul className="invitation-list">
                {invitationPayload.items.map((item) => (
                  <li key={item.id}>
                    <strong>{item.full_name}</strong>
                    <span>{item.email}</span>
                    <span>{item.role_code} · {item.status}</span>
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
            <CompanySettingsForm settings={settings} locale={lang} />
          </section>
        )}
      </section>
    </main>
  );
}
