"use client";

import { useActionState } from "react";

import {
  replaceBranchSupervisorsAction,
  updateBranchAction,
  type OrganizationActionState,
} from "./actions";
import { LocationMapPicker } from "./location-map-picker";

export type BranchMemberOption = { id: string; name: string };

export type EditableBranch = {
  id: string;
  code: string;
  name: string;
  full_address: string;
  saudi_short_address: string | null;
  latitude: string;
  longitude: string;
  geofence_radius_m: number;
  timezone: string;
  manager_membership_id: string | null;
  version: number;
};

const initialState: OrganizationActionState = { message: "" };

export function BranchEditForm({
  locale,
  branch,
  managerOptions,
  supervisorOptions,
  supervisorIds,
  supervisorVersion,
}: {
  locale: string;
  branch: EditableBranch;
  managerOptions: BranchMemberOption[];
  supervisorOptions: BranchMemberOption[];
  supervisorIds: string[];
  supervisorVersion: number;
}) {
  const ar = locale === "ar";
  const [state, action, pending] = useActionState(
    updateBranchAction.bind(null, locale, branch.id),
    initialState,
  );
  const [supervisorState, supervisorAction, supervisorPending] = useActionState(
    replaceBranchSupervisorsAction.bind(null, locale, branch.id),
    initialState,
  );
  return (
    <details>
      <summary>{ar ? "تفاصيل وتعديل الفرع" : "Branch details and edit"}</summary>
      <form action={action} className="portal-form branch-form">
        <input type="hidden" name="version" value={branch.version} />
        <label>{ar ? "رمز الفرع" : "Branch code"}<input name="code" defaultValue={branch.code} required /></label>
        <label>{ar ? "اسم الفرع" : "Branch name"}<input name="name" defaultValue={branch.name} required /></label>
        <label>{ar ? "العنوان المختصر" : "Saudi short address"}<input name="saudi_short_address" defaultValue={branch.saudi_short_address ?? ""} /></label>
        <label>{ar ? "العنوان الكامل" : "Full address"}<input name="full_address" defaultValue={branch.full_address} required /></label>
        <LocationMapPicker locale={locale} initialLatitude={branch.latitude} initialLongitude={branch.longitude} />
        <label>{ar ? "نطاق الحضور بالمتر" : "Geofence radius (m)"}<input name="geofence_radius_m" type="number" min="20" max="10000" defaultValue={branch.geofence_radius_m} required /></label>
        <label>{ar ? "المنطقة الزمنية" : "Timezone"}<input name="timezone" defaultValue={branch.timezone} required /></label>
        <label>
          {ar ? "مدير الفرع" : "Branch manager"}
          <select name="manager_membership_id" defaultValue={branch.manager_membership_id ?? ""}>
            <option value="">{ar ? "بدون مدير محدد" : "No assigned manager"}</option>
            {managerOptions.map((option) => <option key={option.id} value={option.id}>{option.name}</option>)}
          </select>
        </label>
        <button type="submit" disabled={pending}>{pending ? (ar ? "جارٍ الحفظ..." : "Saving...") : (ar ? "حفظ الفرع" : "Save branch")}</button>
        <p className={state.success ? "form-success" : "form-error"} aria-live="polite">{state.message}</p>
      </form>
      <form action={supervisorAction} className="portal-form branch-form">
        <input type="hidden" name="version" value={supervisorVersion} />
        <fieldset>
          <legend>{ar ? "مشرفو الفرع" : "Branch supervisors"}</legend>
          {supervisorOptions.length === 0 ? (
            <p>{ar ? "لا يوجد أعضاء بدور المشرف." : "No members currently have the supervisor role."}</p>
          ) : supervisorOptions.map((option) => (
            <label className="checkbox-field" key={option.id}>
              <input type="checkbox" name="membership_ids" value={option.id} defaultChecked={supervisorIds.includes(option.id)} />
              {option.name}
            </label>
          ))}
        </fieldset>
        <button type="submit" disabled={supervisorPending}>
          {supervisorPending ? (ar ? "جارٍ الحفظ..." : "Saving...") : (ar ? "حفظ المشرفين" : "Save supervisors")}
        </button>
        <p className={supervisorState.success ? "form-success" : "form-error"} aria-live="polite">{supervisorState.message}</p>
      </form>
    </details>
  );
}
