"use client";

import { useActionState } from "react";

import { assignShiftAction, type OrganizationActionState } from "./actions";

const initialState: OrganizationActionState = { message: "" };

type ShiftOption = {
  id: string;
  code: string;
  name: string;
  start_time: string;
  end_time: string;
};

type EmployeeOption = {
  membership_id: string;
  display_name: string;
  email: string;
  role_code: string;
  membership_status: string;
};

type BranchOption = {
  id: string;
  code: string;
  name: string;
};

export type ShiftAssignment = {
  id: string;
  shift_id: string;
  shift_code: string;
  shift_name: string;
  membership_id: string | null;
  branch_id: string | null;
  effective_from: string;
  effective_to: string | null;
};

export function ShiftAssignmentForm({
  locale,
  shifts,
  employees,
  branches,
  assignments,
}: {
  locale: string;
  shifts: ShiftOption[];
  employees: EmployeeOption[];
  branches: BranchOption[];
  assignments: ShiftAssignment[];
}) {
  const ar = locale === "ar";
  const action = assignShiftAction.bind(null, locale);
  const [state, formAction, pending] = useActionState(action, initialState);
  const today = new Date().toISOString().slice(0, 10);
  const employeeById = new Map(employees.map((employee) => [employee.membership_id, employee]));
  const branchById = new Map(branches.map((branch) => [branch.id, branch]));
  const activeEmployees = employees.filter(
    (employee) => employee.membership_status === "active" && employee.role_code !== "OWNER",
  );

  return (
    <section className="assignment-panel" aria-labelledby="shift-assignment-title">
      <div>
        <h3 id="shift-assignment-title">{ar ? "تعيين وردية" : "Assign shift"}</h3>
        <p>
          {ar
            ? "الحضور يحتاج وردية معيّنة للفرع أو للموظف، وليس مجرد إنشاء وردية."
            : "Attendance needs a shift assigned to the branch or employee, not only a created shift."}
        </p>
      </div>
      <form action={formAction} className="portal-form assignment-form">
        <label>
          {ar ? "الوردية" : "Shift"}
          <select name="shift_id" required>
            <option value="">{ar ? "اختر الوردية" : "Select shift"}</option>
            {shifts.map((shift) => (
              <option key={shift.id} value={shift.id}>
                {shift.name} · {shift.code} · {shift.start_time.slice(0, 5)}-{shift.end_time.slice(0, 5)}
              </option>
            ))}
          </select>
        </label>
        <label>
          {ar ? "التعيين على" : "Assign to"}
          <select name="target_type" defaultValue="branch" required>
            <option value="branch">{ar ? "فرع كامل" : "Whole branch"}</option>
            <option value="employee">{ar ? "موظف واحد" : "One employee"}</option>
          </select>
        </label>
        <label>
          {ar ? "الفرع" : "Branch"}
          <select name="branch_id">
            <option value="">{ar ? "اختر الفرع إذا كان التعيين للفرع" : "Select branch for branch assignment"}</option>
            {branches.map((branch) => (
              <option key={branch.id} value={branch.id}>{branch.name} · {branch.code}</option>
            ))}
          </select>
        </label>
        <label>
          {ar ? "الموظف" : "Employee"}
          <select name="membership_id">
            <option value="">{ar ? "اختر الموظف إذا كان التعيين لموظف" : "Select employee for employee assignment"}</option>
            {activeEmployees.map((employee) => (
              <option key={employee.membership_id} value={employee.membership_id}>
                {employee.display_name} · {employee.email}
              </option>
            ))}
          </select>
        </label>
        <label>{ar ? "سارية من" : "Effective from"}<input name="effective_from" type="date" defaultValue={today} required /></label>
        <label>{ar ? "سارية حتى" : "Effective to"}<input name="effective_to" type="date" /></label>
        <button type="submit" disabled={pending}>
          {pending ? (ar ? "جارٍ التعيين..." : "Assigning...") : (ar ? "تعيين الوردية" : "Assign shift")}
        </button>
        <p className={state.success ? "form-success" : "form-error"} aria-live="polite">{state.message}</p>
      </form>
      <div className="assignment-list">
        {assignments.length === 0 ? (
          <p className="empty-state">
            {ar ? "لا توجد تعيينات ورديات بعد." : "No shift assignments yet."}
          </p>
        ) : assignments.map((assignment) => {
          const branch = assignment.branch_id ? branchById.get(assignment.branch_id) : null;
          const employee = assignment.membership_id ? employeeById.get(assignment.membership_id) : null;
          return (
            <article className="assignment-row" key={assignment.id}>
              <div>
                <strong>{assignment.shift_name}</strong>
                <span>{assignment.shift_code} · {assignment.effective_from}{assignment.effective_to ? ` → ${assignment.effective_to}` : ""}</span>
              </div>
              <span className="status-pill">
                {branch
                  ? (ar ? `فرع: ${branch.name}` : `Branch: ${branch.name}`)
                  : employee
                    ? (ar ? `موظف: ${employee.display_name}` : `Employee: ${employee.display_name}`)
                    : (ar ? "هدف غير معروف" : "Unknown target")}
              </span>
            </article>
          );
        })}
      </div>
    </section>
  );
}
