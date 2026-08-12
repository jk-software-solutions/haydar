"use client";

import { useActionState } from "react";

import { assignEmployeeToBranchAction, type OrganizationActionState } from "./actions";

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

export type BranchAssignment = {
  id: string;
  membership_id: string;
  branch_id: string;
  branch_code: string;
  branch_name: string;
  effective_from: string;
  effective_to: string | null;
  reason: string;
};

const initialState: OrganizationActionState = { message: "" };

export function BranchAssignmentForm({
  locale,
  employees,
  branches,
  assignmentsByMember,
}: {
  locale: string;
  employees: EmployeeOption[];
  branches: BranchOption[];
  assignmentsByMember: Record<string, BranchAssignment[]>;
}) {
  const ar = locale === "ar";
  const today = new Date().toISOString().slice(0, 10);
  const [state, action, pending] = useActionState(
    assignEmployeeToBranchAction.bind(null, locale),
    initialState,
  );
  const assignableEmployees = employees.filter(
    (employee) => employee.membership_status === "active" && employee.role_code !== "OWNER",
  );
  const canSubmit = assignableEmployees.length > 0 && branches.length > 0;

  return (
    <article className="operation-form-card assignment-panel">
      <div className="section-heading">
        <div>
          <h3>{ar ? "تعيين موظف لفرع" : "Assign employee to branch"}</h3>
          <p>
            {ar
              ? "اختر الموظف والفرع وتاريخ بداية التعيين."
              : "Choose the employee, branch, and effective start date."}
          </p>
        </div>
      </div>
      <form action={action} className="portal-form assignment-form">
        <label>
          {ar ? "الموظف" : "Employee"}
          <select name="membership_id" required disabled={!canSubmit}>
            <option value="">{ar ? "اختر موظف" : "Select employee"}</option>
            {assignableEmployees.map((employee) => (
              <option key={employee.membership_id} value={employee.membership_id}>
                {employee.display_name} - {employee.email}
              </option>
            ))}
          </select>
        </label>
        <label>
          {ar ? "الفرع" : "Branch"}
          <select name="branch_id" required disabled={!canSubmit}>
            <option value="">{ar ? "اختر فرع" : "Select branch"}</option>
            {branches.map((branch) => (
              <option key={branch.id} value={branch.id}>
                {branch.name} - {branch.code}
              </option>
            ))}
          </select>
        </label>
        <label>
          {ar ? "تاريخ البدء" : "Effective from"}
          <input name="effective_from" type="date" defaultValue={today} required disabled={!canSubmit} />
        </label>
        <label>
          {ar ? "سبب التعيين" : "Reason"}
          <input
            name="reason"
            minLength={5}
            maxLength={1000}
            required
            disabled={!canSubmit}
            placeholder={ar ? "مثلاً: تعيين تشغيلي" : "Example: operational assignment"}
          />
        </label>
        <button type="submit" disabled={!canSubmit || pending}>
          {pending ? (ar ? "جارٍ التعيين..." : "Assigning...") : (ar ? "تعيين للفرع" : "Assign to branch")}
        </button>
        <p className={state.success ? "form-success" : "form-error"} aria-live="polite">
          {state.message}
        </p>
      </form>
      <div className="assignment-list">
        {assignableEmployees.length === 0 ? (
          <p>{ar ? "لا يوجد موظفون نشطون للتعيين." : "No active employees are available for assignment."}</p>
        ) : (
          assignableEmployees.map((employee) => {
            const history = assignmentsByMember[employee.membership_id] ?? [];
            const current = history.find((assignment) => assignment.effective_to === null);
            return (
              <div className="assignment-row" key={employee.membership_id}>
                <div>
                  <strong>{employee.display_name}</strong>
                  <span>{employee.email}</span>
                </div>
                {current ? (
                  <div>
                    <strong>{current.branch_name}</strong>
                    <span>
                      {ar ? "من" : "From"} {current.effective_from} {current.effective_to ? `${ar ? "حتى" : "until"} ${current.effective_to}` : (ar ? "بدون تاريخ نهاية" : "open-ended")}
                    </span>
                  </div>
                ) : (
                  <span className="status-pill">{ar ? "بدون فرع حالي" : "No current branch"}</span>
                )}
              </div>
            );
          })
        )}
      </div>
    </article>
  );
}
