"use client";

import { useActionState } from "react";

import { updateMemberAccessAction, type AccessActionState } from "./access-actions";

type Option = { id: string; name: string };
type Permission = { code: string; description: string };
type PermissionCopy = { label: string; description: string };
export type MemberAccess = {
  membership_id: string;
  role_codes: string[];
  permission_overrides: Record<string, boolean>;
  effective_permissions: string[];
  branch_ids: string[];
  department_ids: string[];
  group_ids: string[];
};

const permissionCopies: Record<string, { ar: PermissionCopy; en: PermissionCopy }> = {
  "members:view": {
    ar: { label: "عرض الموظفين", description: "عرض عضويات الشركة والدعوات." },
    en: { label: "View employees", description: "View company memberships and invitations." },
  },
  "members:create": {
    ar: { label: "دعوة موظفين", description: "إرسال دعوات لموظفين جدد." },
    en: { label: "Invite employees", description: "Invite new company members." },
  },
  "members:manage": {
    ar: { label: "إدارة الموظفين", description: "تحديث العضويات والأدوار." },
    en: { label: "Manage employees", description: "Update company memberships and roles." },
  },
  "settings:manage": {
    ar: { label: "إعدادات الشركة", description: "تعديل إعدادات الشركة العامة." },
    en: { label: "Company settings", description: "Manage company settings." },
  },
  "devices:view": {
    ar: { label: "عرض الأجهزة", description: "عرض أجهزة الموظفين وطلبات تغيير الجهاز." },
    en: { label: "View devices", description: "View device registrations and change requests." },
  },
  "devices:manage": {
    ar: { label: "إدارة الأجهزة", description: "قبول أو رفض طلبات تغيير جهاز الموظف." },
    en: { label: "Manage devices", description: "Approve or reject employee device changes." },
  },
  "branches:view": {
    ar: { label: "عرض الفروع", description: "عرض فروع الشركة." },
    en: { label: "View branches", description: "View company branches." },
  },
  "branches:manage": {
    ar: { label: "إدارة الفروع", description: "إنشاء وتحديث فروع الشركة." },
    en: { label: "Manage branches", description: "Create and update company branches." },
  },
  "departments:view": {
    ar: { label: "عرض الأقسام", description: "عرض أقسام الشركة." },
    en: { label: "View departments", description: "View company departments." },
  },
  "departments:manage": {
    ar: { label: "إدارة الأقسام", description: "إنشاء وتحديث أقسام الشركة." },
    en: { label: "Manage departments", description: "Create and update company departments." },
  },
  "assignments:view": {
    ar: { label: "عرض التعيينات", description: "عرض سجل تعيين الموظفين على الفروع." },
    en: { label: "View assignments", description: "View employee branch assignment history." },
  },
  "assignments:manage": {
    ar: { label: "إدارة التعيينات", description: "تعيين ونقل الموظفين بين الفروع." },
    en: { label: "Manage assignments", description: "Assign and transfer employees between branches." },
  },
  "shifts:view": {
    ar: { label: "عرض الورديات", description: "عرض ورديات الشركة وتعييناتها." },
    en: { label: "View shifts", description: "View company shifts and assignments." },
  },
  "shifts:manage": {
    ar: { label: "إدارة الورديات", description: "إنشاء وتعيين ورديات الشركة." },
    en: { label: "Manage shifts", description: "Create and assign company shifts." },
  },
  "attendance:view": {
    ar: { label: "عرض الحضور", description: "عرض سجلات حضور وانصراف الموظفين." },
    en: { label: "View attendance", description: "View tenant attendance records." },
  },
  "attendance:manage": {
    ar: { label: "إدارة الحضور", description: "إنشاء وتصحيح سجلات الحضور." },
    en: { label: "Manage attendance", description: "Create and correct attendance records." },
  },
  "permissions:view": {
    ar: { label: "عرض الاستئذانات", description: "عرض طلبات استئذان الموظفين." },
    en: { label: "View permissions", description: "View employee permission requests." },
  },
  "permissions:manage": {
    ar: { label: "إدارة الاستئذانات", description: "مراجعة طلبات الاستئذان وقبولها أو رفضها." },
    en: { label: "Manage permissions", description: "Review employee permission requests." },
  },
  "presence:manage": {
    ar: { label: "إثبات التواجد", description: "إنشاء ومراجعة طلبات إثبات التواجد." },
    en: { label: "Proof of presence", description: "Create and review presence requests." },
  },
  "geofence_exits:view": {
    ar: { label: "عرض مغادرة النطاق", description: "عرض أحداث مغادرة النطاق غير المصرح بها." },
    en: { label: "View geofence exits", description: "View unauthorized geofence exit events." },
  },
  "geofence_exits:manage": {
    ar: { label: "إدارة مغادرة النطاق", description: "مراجعة أحداث مغادرة النطاق غير المصرح بها." },
    en: { label: "Manage geofence exits", description: "Review unauthorized geofence exit events." },
  },
  "tasks:view": {
    ar: { label: "عرض المهام", description: "عرض المهام المسندة." },
    en: { label: "View tasks", description: "View assigned tenant tasks." },
  },
  "tasks:manage": {
    ar: { label: "إدارة المهام", description: "إنشاء وإدارة مهام العمل." },
    en: { label: "Manage tasks", description: "Create and manage tenant tasks." },
  },
  "leave:view": {
    ar: { label: "عرض الإجازات", description: "عرض طلبات الإجازة والأرصدة." },
    en: { label: "View leave", description: "View tenant leave requests and balances." },
  },
  "leave:manage": {
    ar: { label: "إدارة الإجازات", description: "إدارة أنواع الإجازات والأرصدة والموافقات." },
    en: { label: "Manage leave", description: "Manage leave types, balances, and approvals." },
  },
  "documents:view": {
    ar: { label: "عرض الوثائق", description: "عرض وثائق الموظفين." },
    en: { label: "View documents", description: "View tenant employee documents." },
  },
  "documents:manage": {
    ar: { label: "إدارة الوثائق", description: "إدارة ومراجعة وثائق الموظفين." },
    en: { label: "Manage documents", description: "Manage and review employee documents." },
  },
  "reports:view": {
    ar: { label: "عرض التقارير", description: "عرض تقارير القوى العاملة." },
    en: { label: "View reports", description: "View tenant workforce reports." },
  },
  "reports:export": {
    ar: { label: "تصدير التقارير", description: "تصدير التقارير إلى ملفات." },
    en: { label: "Export reports", description: "Export tenant reports." },
  },
  "subscription:view": {
    ar: { label: "عرض الاشتراك", description: "عرض اشتراك الشركة." },
    en: { label: "View subscription", description: "View the company subscription." },
  },
  "subscription:manage": {
    ar: { label: "إدارة الاشتراك", description: "إدارة طلبات اشتراك الشركة." },
    en: { label: "Manage subscription", description: "Manage company subscription requests." },
  },
};

function permissionCopy(permission: Permission, ar: boolean): PermissionCopy {
  return permissionCopies[permission.code]?.[ar ? "ar" : "en"] ?? {
    label: permission.code,
    description: permission.description,
  };
}

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
    <details className="operation-form-card access-card">
      <summary>{ar ? "الأدوار والصلاحيات والنطاق" : "Roles, permissions, and scope"}</summary>
      <form action={formAction} className="portal-form access-form">
        <fieldset className="access-fieldset">
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
        <fieldset className="access-fieldset permission-overrides">
          <legend>{ar ? "تخصيص الصلاحيات" : "Permission overrides"}</legend>
          {permissions.map((permission) => {
            const override = member.permission_overrides[permission.code];
            const copy = permissionCopy(permission, ar);
            return (
              <label className="permission-override" key={permission.code}>
                <span>
                  <strong>{copy.label}</strong>
                  <small>{copy.description}</small>
                </span>
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
  const ar = title.includes("نطاق");
  return (
    <fieldset className="access-fieldset scope-fieldset">
      <legend>{title}</legend>
      {options.length === 0 ? <small>{ar ? "لا توجد خيارات متاحة." : "No options available."}</small> : options.map((option) => (
        <label className="checkbox-field" key={option.id}>
          <input type="checkbox" name={name} value={option.id} defaultChecked={selected.includes(option.id)} />
          {option.name}
        </label>
      ))}
    </fieldset>
  );
}
