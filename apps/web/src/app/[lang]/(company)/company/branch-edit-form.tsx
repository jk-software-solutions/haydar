"use client";

import { useActionState } from "react";

import { updateBranchAction, type OrganizationActionState } from "./actions";

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
  version: number;
};

const initialState: OrganizationActionState = { message: "" };

export function BranchEditForm({ locale, branch }: { locale: string; branch: EditableBranch }) {
  const ar = locale === "ar";
  const [state, action, pending] = useActionState(
    updateBranchAction.bind(null, locale, branch.id),
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
        <label>{ar ? "خط العرض" : "Latitude"}<input name="latitude" type="number" step="0.000001" defaultValue={branch.latitude} required /></label>
        <label>{ar ? "خط الطول" : "Longitude"}<input name="longitude" type="number" step="0.000001" defaultValue={branch.longitude} required /></label>
        <label>{ar ? "نطاق الحضور بالمتر" : "Geofence radius (m)"}<input name="geofence_radius_m" type="number" min="20" max="10000" defaultValue={branch.geofence_radius_m} required /></label>
        <label>{ar ? "المنطقة الزمنية" : "Timezone"}<input name="timezone" defaultValue={branch.timezone} required /></label>
        <button type="submit" disabled={pending}>{pending ? (ar ? "جارٍ الحفظ..." : "Saving...") : (ar ? "حفظ الفرع" : "Save branch")}</button>
        <p className={state.success ? "form-success" : "form-error"} aria-live="polite">{state.message}</p>
      </form>
    </details>
  );
}
