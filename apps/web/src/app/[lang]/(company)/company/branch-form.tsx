"use client";

import { useActionState } from "react";

import { createBranchAction, type OrganizationActionState } from "./actions";
import { LocationMapPicker } from "./location-map-picker";

const initialState: OrganizationActionState = { message: "" };

export function BranchForm({ locale }: { locale: string }) {
  const ar = locale === "ar";
  const action = createBranchAction.bind(null, locale);
  const [state, formAction, pending] = useActionState(action, initialState);
  return (
    <form action={formAction} className="portal-form branch-form">
      <label>{ar ? "رمز الفرع" : "Branch code"}<input name="code" placeholder="RUH-01" required /></label>
      <label>{ar ? "اسم الفرع" : "Branch name"}<input name="name" required /></label>
      <label>{ar ? "العنوان المختصر" : "Saudi short address"}<input name="saudi_short_address" /></label>
      <label>{ar ? "العنوان الكامل" : "Full address"}<input name="full_address" required /></label>
      <LocationMapPicker locale={locale} />
      <label>{ar ? "نطاق الحضور بالمتر" : "Geofence radius (m)"}<input name="geofence_radius_m" type="number" min="20" max="10000" defaultValue="100" required /></label>
      <label>{ar ? "المنطقة الزمنية" : "Timezone"}<input name="timezone" defaultValue="Asia/Riyadh" required /></label>
      <label>
        {ar ? "شبكات Wi‑Fi المسموحة للحضور" : "Authorized Wi‑Fi networks"}
        <textarea name="wifi_networks" rows={3} placeholder={ar ? "اسم الشبكة|عنوان BSSID لكل سطر (اختياري)" : "SSID|BSSID per line (optional)"} />
        <small>{ar ? "اتصل بالشبكة من هاتف الموظف؛ يمكن معرفة BSSID من إعدادات الراوتر." : "The employee must be connected to one of these networks. Find the BSSID in the router settings."}</small>
      </label>
      <button type="submit" disabled={pending}>{pending ? (ar ? "جارٍ الإنشاء..." : "Creating...") : (ar ? "إضافة الفرع" : "Add branch")}</button>
      <p className={state.success ? "form-success" : "form-error"} aria-live="polite">{state.message}</p>
    </form>
  );
}
