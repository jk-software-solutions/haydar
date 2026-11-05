"use client";

import { useActionState } from "react";

import {
  assignEmployeeToBranchAction,
  assignShiftAction,
  deactivateEmployeeAction,
  updateEmployeeAction,
  updateEmployeeStatusAction,
  uploadEmployeeAvatarAction,
  type OrganizationActionState,
} from "./actions";
import type { BranchAssignment } from "./branch-assignment-form";
import type { ShiftAssignment } from "./shift-assignment-form";

export type EditableEmployee = {
  membership_id: string;
  display_name: string;
  email: string;
  role_code: string;
  membership_status: string;
  membership_version: number;
  employee_number: string | null;
  avatar_file_id?: string | null;
  phone: string | null;
  phone_login_enabled?: boolean;
  job_title: string | null;
  employment_type: string;
  preferred_locale: string;
  attendance_enabled: boolean;
  version: number;
};

const initialState: OrganizationActionState = { message: "" };

type AssignmentBranch = { id: string; code: string; name: string };
type AssignmentShift = { id: string; code: string; name: string; start_time: string; end_time: string };

export function EmployeeForm({
  employee,
  locale,
  branches = [],
  shifts = [],
  currentBranchAssignment = null,
  currentShiftAssignment = null,
}: {
  employee: EditableEmployee;
  locale: string;
  branches?: AssignmentBranch[];
  shifts?: AssignmentShift[];
  currentBranchAssignment?: BranchAssignment | null;
  currentShiftAssignment?: ShiftAssignment | null;
}) {
  const ar = locale === "ar";
  const today = new Date().toISOString().slice(0, 10);
  const action = updateEmployeeAction.bind(null, locale, employee.membership_id);
  const [state, formAction, pending] = useActionState(action, initialState);
  const statusAction = updateEmployeeStatusAction.bind(null, locale, employee.membership_id);
  const [statusState, statusFormAction, statusPending] = useActionState(statusAction, initialState);
  const avatarAction = uploadEmployeeAvatarAction.bind(null, locale, employee.membership_id);
  const [avatarState, avatarFormAction, avatarPending] = useActionState(avatarAction, {});
  const branchAction = assignEmployeeToBranchAction.bind(null, locale);
  const [branchState, branchFormAction, branchPending] = useActionState(branchAction, initialState);
  const shiftAction = assignShiftAction.bind(null, locale);
  const [shiftState, shiftFormAction, shiftPending] = useActionState(shiftAction, initialState);
  const deleteAction = deactivateEmployeeAction.bind(null, locale, employee.membership_id, employee.membership_version);
  const canAssign = employee.role_code !== "OWNER" && employee.membership_status === "active";
  return (
    <details className="employee-card">
      <summary>
        <span className="employee-summary">
          {employee.avatar_file_id ? <img className="employee-avatar" src={`/api/files/${employee.avatar_file_id}`} alt="" /> : <span className="employee-avatar employee-avatar-placeholder" aria-hidden="true">{employee.display_name.slice(0, 1).toUpperCase()}</span>}
          <span><strong>{employee.display_name}</strong><small>{employee.email}</small></span>
        </span>
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
      <form action={avatarFormAction} className="portal-form employee-form avatar-form">
        <input type="hidden" name="version" value={employee.version} />
        <label>{ar ? "صورة الموظف" : "Employee photo"}<input name="avatar" type="file" accept=".jpg,.jpeg,.png,.webp" required /></label>
        <button type="submit" disabled={avatarPending}>{avatarPending ? (ar ? "جارٍ رفع الصورة..." : "Uploading photo...") : (ar ? "حفظ صورة الموظف" : "Save employee photo")}</button>
        {avatarState.message && <p className={avatarState.success ? "form-success" : "form-error"} aria-live="polite">{avatarState.message}</p>}
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
      {canAssign && (
        <section className="assignment-panel employee-assignment-panel">
          <div>
            <h3>{ar ? "تعيين الفرع والوردية" : "Branch and shift assignment"}</h3>
            <p>
              {currentBranchAssignment
                ? `${ar ? "الفرع الحالي" : "Current branch"}: ${currentBranchAssignment.branch_name}`
                : ar ? "لا يوجد فرع حالي." : "No current branch."}
              {" · "}
              {currentShiftAssignment
                ? `${ar ? "الوردية الحالية" : "Current shift"}: ${currentShiftAssignment.shift_name}`
                : ar ? "لا توجد وردية مباشرة للموظف." : "No direct employee shift."}
            </p>
          </div>
          <form action={branchFormAction} className="portal-form employee-form">
            <input type="hidden" name="membership_ids" value={employee.membership_id} />
            <label>
              {ar ? "الفرع" : "Branch"}
              <select name="branch_id" required disabled={branches.length === 0}>
                <option value="">{ar ? "اختر الفرع" : "Select branch"}</option>
                {branches.map((branch) => (
                  <option key={branch.id} value={branch.id}>
                    {branch.name} · {branch.code}
                  </option>
                ))}
              </select>
            </label>
            <label>{ar ? "سارية من" : "Effective from"}<input name="effective_from" type="date" defaultValue={today} required /></label>
            <input name="reason" minLength={5} maxLength={1000} required placeholder={ar ? "سبب تعيين الفرع" : "Branch assignment reason"} />
            <button type="submit" disabled={branchPending || branches.length === 0}>
              {branchPending ? (ar ? "جارٍ التعيين..." : "Assigning...") : (ar ? "تعيين الفرع" : "Assign branch")}
            </button>
            <p className={branchState.success ? "form-success" : "form-error"} aria-live="polite">{branchState.message}</p>
          </form>
          <form action={shiftFormAction} className="portal-form employee-form">
            <input type="hidden" name="target_type" value="employee" />
            <input type="hidden" name="membership_id" value={employee.membership_id} />
            <label>
              {ar ? "الوردية" : "Shift"}
              <select name="shift_id" required disabled={shifts.length === 0}>
                <option value="">{ar ? "اختر الوردية" : "Select shift"}</option>
                {shifts.map((shift) => (
                  <option key={shift.id} value={shift.id}>
                    {shift.name} · {shift.code} · {shift.start_time.slice(0, 5)}-{shift.end_time.slice(0, 5)}
                  </option>
                ))}
              </select>
            </label>
            <label>{ar ? "سارية من" : "Effective from"}<input name="effective_from" type="date" defaultValue={today} required /></label>
            <label>{ar ? "سارية حتى" : "Effective to"}<input name="effective_to" type="date" /></label>
            <button type="submit" disabled={shiftPending || shifts.length === 0}>
              {shiftPending ? (ar ? "جارٍ التعيين..." : "Assigning...") : (ar ? "تعيين الوردية" : "Assign shift")}
            </button>
            <p className={shiftState.success ? "form-success" : "form-error"} aria-live="polite">{shiftState.message}</p>
          </form>
        </section>
      )}
      {employee.role_code !== "OWNER" && employee.membership_status !== "inactive" && (
        <form action={deleteAction} className="inline-action">
          <button type="submit" className="danger-button">
            {ar ? "حذف / تعطيل الموظف" : "Delete / deactivate employee"}
          </button>
        </form>
      )}
    </details>
  );
}
