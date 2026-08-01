import { redirect } from "next/navigation";

import { authorizedApiFetch, getWebSession } from "@/lib/auth/server-session";
import { canEnterCompanyPortal, type PortalRole } from "@/lib/auth/permissions";

import { logoutAction } from "./actions";
import { InvitationForm } from "./invitation-form";

type Invitation = {
  id: string;
  full_name: string;
  email: string;
  role_code: string;
  status: string;
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
  const response = canManage ? await authorizedApiFetch("/invitations") : null;
  const payload: { items: Invitation[] } = response?.ok
    ? ((await response.json()) as { items: Invitation[] })
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
        {canManage ? (
          <>
            <h2>{ar ? "دعوات الموظفين" : "Employee invitations"}</h2>
            <InvitationForm locale={lang} />
            {payload.items.length === 0 ? (
              <p>{ar ? "لا توجد دعوات بعد." : "No invitations yet."}</p>
            ) : (
              <ul className="invitation-list">
                {payload.items.map((item) => (
                  <li key={item.id}>
                    <strong>{item.full_name}</strong>
                    <span>{item.email}</span>
                    <span>{item.role_code} · {item.status}</span>
                  </li>
                ))}
              </ul>
            )}
          </>
        ) : (
          <p>{ar ? "ليست لديك صلاحية لإدارة الدعوات." : "You cannot manage invitations."}</p>
        )}
      </section>
    </main>
  );
}
