import { redirect } from "next/navigation";

import { authorizedApiFetch, getWebSession } from "@/lib/auth/server-session";
import { canEnterCompanyPortal, type PortalRole } from "@/lib/auth/permissions";

import { archiveBranchAction, logoutAction } from "./actions";
import { BranchForm } from "./branch-form";
import { CompanySettingsForm, type CompanySettings } from "./company-settings-form";
import { EmployeeForm, type EditableEmployee } from "./employee-form";
import { InvitationForm } from "./invitation-form";

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
  const [invitationResponse, employeeResponse, settingsResponse, branchResponse] = await Promise.all([
    canManage ? authorizedApiFetch("/invitations") : Promise.resolve(null),
    authorizedApiFetch("/employees?page_size=100"),
    authorizedApiFetch("/companies/current"),
    authorizedApiFetch("/branches?page_size=100"),
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
                <EmployeeForm key={employee.membership_id} employee={employee} locale={lang} />
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
