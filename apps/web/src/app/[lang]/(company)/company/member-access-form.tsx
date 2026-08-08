"use client";

import { useActionState } from "react";

import { updateMemberAccessAction, type AccessActionState } from "./access-actions";

type Option = { id: string; name: string };
type Permission = { code: string; description: string };
export type MemberAccess = {
  membership_id: string;
  role_codes: string[];
  permission_overrides: Record<string, boolean>;
  effective_permissions: string[];
  branch_ids: string[];
  department_ids: string[];
  group_ids: string[];
};

export function MemberAccessForm({
  locale,
  member,
  permissions,
  branches,
  departments,
  groups,
}: {
  locale: string;
  member: MemberAccess;
  permissions: Permission[];
  branches: Option[];
  departments: Option[];
  groups: Option[];
}) {
  const ar = locale === "ar";
  const action = updateMemberAccessAction.bind(null, locale, member.membership_id);
  const [state, formAction, pending] = useActionState<AccessActionState, FormData>(
    action,
    { message: "" },
  );
  return (
    <details className="operation-form-card">
      <summary>{ar ? "الأدوار والصلاحيات والنطاق" : "Roles, permissions, and scope"}</summary>
      <form action={formAction} className="portal-form">
        <fieldset>
          <legend>{ar ? "الأدوار" : "Roles"}</legend>
          {[
            ["MANAGER", ar ? "مدير" : "Manager"],
            ["SUPERVISOR", ar ? "مشرف" : "Supervisor"],
            ["HR_OFFICER", ar ? "موارد بشرية" : "HR officer"],
            ["EMPLOYEE", ar ? "موظف" : "Employee"],
          ].map(([code, label]) => (
            <label className="checkbox-field" key={code}>
              <input type="checkbox" name="role_codes" value={code} defaultChecked={member.role_codes.includes(code)} />
              {label}
            </label>
          ))}
        </fieldset>
        <fieldset>
          <legend>{ar ? "تخصيص الصلاحيات" : "Permission overrides"}</legend>
          {permissions.map((permission) => {
            const override = member.permission_overrides[permission.code];
            return (
              <label key={permission.code}>
                <span>{permission.code} · {permission.description}</span>
                <select name={`permission::${permission.code}`} defaultValue={override === undefined ? "inherit" : override ? "allow" : "deny"}>
                  <option value="inherit">{ar ? "حسب الدور" : "Inherit role"}</option>
                  <option value="allow">{ar ? "سماح" : "Allow"}</option>
                  <option value="deny">{ar ? "منع" : "Deny"}</option>
                </select>
              </label>
            );
          })}
        </fieldset>
        <ScopeOptions title={ar ? "نطاق الفروع" : "Branch scope"} name="branch_ids" options={branches} selected={member.branch_ids} />
        <ScopeOptions title={ar ? "نطاق الأقسام" : "Department scope"} name="department_ids" options={departments} selected={member.department_ids} />
        <ScopeOptions title={ar ? "نطاق المجموعات" : "Group scope"} name="group_ids" options={groups} selected={member.group_ids} />
        <button type="submit" disabled={pending}>
          {pending ? ar ? "جارٍ الحفظ..." : "Saving..." : ar ? "حفظ الوصول" : "Save access"}
        </button>
        <p className={state.success ? "form-success" : "form-error"} aria-live="polite">{state.message}</p>
      </form>
    </details>
  );
}

function ScopeOptions({ title, name, options, selected }: { title: string; name: string; options: Option[]; selected: string[] }) {
  return (
    <fieldset>
      <legend>{title}</legend>
      {options.length === 0 ? <small>No options available.</small> : options.map((option) => (
        <label className="checkbox-field" key={option.id}>
          <input type="checkbox" name={name} value={option.id} defaultChecked={selected.includes(option.id)} />
          {option.name}
        </label>
      ))}
    </fieldset>
  );
}
