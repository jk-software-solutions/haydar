"use client";

import { useActionState } from "react";

import { updateEmployeeAction, updateEmployeeStatusAction, type OrganizationActionState } from "./actions";

export type EditableEmployee = {
  membership_id: string;
  display_name: string;
  email: string;
  role_code: string;
  membership_status: string;
  membership_version: number;
  employee_number: string | null;
  phone: string | null;
  phone_login_enabled?: boolean;
  job_title: string | null;
  employment_type: string;
  preferred_locale: string;
  attendance_enabled: boolean;
  version: number;
};

const initialState: OrganizationActionState = { message: "" };

export function EmployeeForm({ employee, locale }: { employee: EditableEmployee; locale: string }) {
  const ar = locale === "ar";
  const action = updateEmployeeAction.bind(null, locale, employee.membership_id);
  const [state, formAction, pending] = useActionState(action, initialState);
  const statusAction = updateEmployeeStatusAction.bind(null, locale, employee.membership_id);
  const [statusState, statusFormAction, statusPending] = useActionState(statusAction, initialState);
  return (
    <details className="employee-card">
      <summary>
        <span><strong>{employee.display_name}</strong><small>{employee.email}</small></span>
        <span>{employee.job_title || employee.role_code}</span>
      </summary>
      <form action={formAction} className="portal-form employee-form">
        <input type="hidden" name="version" value={employee.version} />
        <label>{ar ? "الاسم" : "Name"}<input name="display_name" defaultValue={employee.display_name} required /></label>
        <label>{ar ? "الرقم الوظيفي" : "Employee number"}<input name="employee_number" defaultValue={employee.employee_number ?? ""} /></label>
        <label>{ar ? "الهاتف الدولي" : "International phone"}<input name="phone" type="tel" placeholder="+966500000000" defaultValue={employee.phone ?? ""} /></label>
        {employee.phone_login_enabled && <small>{ar ? "تم تفعيل تسجيل الدخول بهذا الرقم بواسطة مسؤول الشركة." : "Phone login is administrator-verified and enabled."}</small>}
        <label>{ar ? "المسمى الوظيفي" : "Job title"}<input name="job_title" defaultValue={employee.job_title ?? ""} /></label>
        <label>{ar ? "نوع التوظيف" : "Employment type"}<select name="employment_type" defaultValue={employee.employment_type}><option value="full_time">{ar ? "دوام كامل" : "Full time"}</option><option value="part_time">{ar ? "دوام جزئي" : "Part time"}</option><option value="contractor">{ar ? "متعاقد" : "Contractor"}</option><option value="temporary">{ar ? "مؤقت" : "Temporary"}</option></select></label>
        <label>{ar ? "اللغة" : "Language"}<select name="preferred_locale" defaultValue={employee.preferred_locale}><option value="ar">العربية</option><option value="en">English</option></select></label>
        <label className="checkbox-field"><input type="checkbox" name="attendance_enabled" defaultChecked={employee.attendance_enabled} />{ar ? "السماح بالحضور" : "Attendance enabled"}</label>
        <button type="submit" disabled={pending}>{pending ? (ar ? "جارٍ الحفظ..." : "Saving...") : (ar ? "حفظ" : "Save")}</button>
        <p className={state.success ? "form-success" : "form-error"} aria-live="polite">{state.message}</p>
      </form>
      {employee.role_code !== "OWNER" && (
        <form action={statusFormAction} className="portal-form employee-form">
          <input type="hidden" name="membership_version" value={employee.membership_version} />
          <label>{ar ? "حالة العضوية" : "Membership status"}<select name="membership_status" defaultValue={employee.membership_status}><option value="active">{ar ? "نشطة" : "Active"}</option><option value="inactive">{ar ? "غير نشطة" : "Inactive"}</option></select></label>
          <input name="status_reason" required minLength={3} placeholder={ar ? "سبب تغيير الحالة" : "Reason for status change"} />
          <button type="submit" disabled={statusPending}>{statusPending ? (ar ? "جارٍ التحديث..." : "Updating...") : (ar ? "تحديث حالة العضوية" : "Update membership status")}</button>
          <p className={statusState.success ? "form-success" : "form-error"} aria-live="polite">{statusState.message}</p>
        </form>
      )}
    </details>
  );
}
