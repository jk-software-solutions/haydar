"use client";

import { useActionState } from "react";

import { updateEmployeeAction, type OrganizationActionState } from "./actions";

export type EditableEmployee = {
  membership_id: string;
  display_name: string;
  email: string;
  role_code: string;
  employee_number: string | null;
  phone: string | null;
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
        <label>{ar ? "الهاتف" : "Phone"}<input name="phone" defaultValue={employee.phone ?? ""} /></label>
        <label>{ar ? "المسمى الوظيفي" : "Job title"}<input name="job_title" defaultValue={employee.job_title ?? ""} /></label>
        <label>{ar ? "نوع التوظيف" : "Employment type"}<select name="employment_type" defaultValue={employee.employment_type}><option value="full_time">{ar ? "دوام كامل" : "Full time"}</option><option value="part_time">{ar ? "دوام جزئي" : "Part time"}</option><option value="contractor">{ar ? "متعاقد" : "Contractor"}</option><option value="temporary">{ar ? "مؤقت" : "Temporary"}</option></select></label>
        <label>{ar ? "اللغة" : "Language"}<select name="preferred_locale" defaultValue={employee.preferred_locale}><option value="ar">العربية</option><option value="en">English</option></select></label>
        <label className="checkbox-field"><input type="checkbox" name="attendance_enabled" defaultChecked={employee.attendance_enabled} />{ar ? "السماح بالحضور" : "Attendance enabled"}</label>
        <button type="submit" disabled={pending}>{pending ? (ar ? "جارٍ الحفظ..." : "Saving...") : (ar ? "حفظ" : "Save")}</button>
        <p className={state.success ? "form-success" : "form-error"} aria-live="polite">{state.message}</p>
      </form>
    </details>
  );
}
