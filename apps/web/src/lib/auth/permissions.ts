export const companyRoles = [
  "OWNER",
  "MANAGER",
  "SUPERVISOR",
  "HR_OFFICER",
  "EMPLOYEE",
] as const;

export type CompanyRole = (typeof companyRoles)[number];
export type PlatformRole = "SUPER_ADMIN";
export type PortalRole = CompanyRole | PlatformRole;

const companyPortalRoles = new Set<PortalRole>([
  "OWNER",
  "MANAGER",
  "SUPERVISOR",
  "HR_OFFICER",
]);

export function canEnterCompanyPortal(role: PortalRole): boolean {
  return companyPortalRoles.has(role);
}

export function canEnterPlatformPortal(role: PortalRole): boolean {
  return role === "SUPER_ADMIN";
}
