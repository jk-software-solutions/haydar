"use client";

import { useActionState } from "react";

import {
  createGroupAction,
  replaceGroupMembersAction,
  updateGroupAction,
  type GroupActionState,
} from "./group-actions";

export type EditableGroup = {
  id: string;
  code: string;
  name: string;
  description: string;
  is_active: boolean;
  version: number;
  membership_ids: string[];
};

type EmployeeOption = { membership_id: string; display_name: string; membership_status: string };
const initialState: GroupActionState = { message: "" };

export function GroupManagement({ locale, groups, employees }: { locale: string; groups: EditableGroup[]; employees: EmployeeOption[] }) {
  const ar = locale === "ar";
  const [state, action, pending] = useActionState(createGroupAction.bind(null, locale), initialState);
  return (
    <section className="portal-section">
      <h2>{ar ? "المجموعات التشغيلية" : "Operational groups"}</h2>
      <form action={action} className="portal-form operation-form">
        <input name="code" required pattern="[A-Za-z0-9_-]+" placeholder={ar ? "الرمز" : "Code"} />
        <input name="name" required minLength={2} placeholder={ar ? "اسم المجموعة" : "Group name"} />
        <input name="description" placeholder={ar ? "الوصف" : "Description"} />
        <button type="submit" disabled={pending}>{pending ? (ar ? "جارٍ الإنشاء..." : "Creating...") : (ar ? "إنشاء مجموعة" : "Create group")}</button>
        <p className={state.success ? "form-success" : "form-error"}>{state.message}</p>
      </form>
      <div className="platform-company-grid">
        {groups.map((group) => <GroupEditor key={group.id} locale={locale} group={group} employees={employees} />)}
      </div>
    </section>
  );
}

function GroupEditor({ locale, group, employees }: { locale: string; group: EditableGroup; employees: EmployeeOption[] }) {
  const ar = locale === "ar";
  const [updateState, updateAction, updating] = useActionState(updateGroupAction.bind(null, locale, group.id), initialState);
  const [memberState, memberAction, updatingMembers] = useActionState(replaceGroupMembersAction.bind(null, locale, group.id), initialState);
  return (
    <article className="operation-form-card">
      <h3>{group.name} · {group.code}</h3>
      <form action={updateAction} className="portal-form">
        <input type="hidden" name="version" value={group.version} />
        <input name="name" defaultValue={group.name} required minLength={2} />
        <input name="description" defaultValue={group.description} />
        <select name="is_active" defaultValue={String(group.is_active)}><option value="true">{ar ? "نشطة" : "Active"}</option><option value="false">{ar ? "مؤرشفة" : "Archived"}</option></select>
        <button type="submit" disabled={updating}>{ar ? "حفظ المجموعة" : "Save group"}</button>
        <p className={updateState.success ? "form-success" : "form-error"}>{updateState.message}</p>
      </form>
      <form action={memberAction} className="portal-form">
        <fieldset>
          <legend>{ar ? "أعضاء المجموعة" : "Group members"}</legend>
          {employees.filter((employee) => employee.membership_status === "active").map((employee) => (
            <label className="checkbox-field" key={employee.membership_id}>
              <input type="checkbox" name="membership_ids" value={employee.membership_id} defaultChecked={group.membership_ids.includes(employee.membership_id)} />
              {employee.display_name}
            </label>
          ))}
        </fieldset>
        <button type="submit" disabled={updatingMembers}>{ar ? "حفظ الأعضاء" : "Save members"}</button>
        <p className={memberState.success ? "form-success" : "form-error"}>{memberState.message}</p>
      </form>
    </article>
  );
}
