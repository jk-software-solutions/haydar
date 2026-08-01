"use client";

import { useActionState } from "react";

import { updateCompanySettingsAction, type OrganizationActionState } from "./actions";

export type CompanySettings = {
  display_name: string;
  default_locale: string;
  timezone: string;
  country_code: string;
  version: number;
};

const initialState: OrganizationActionState = { message: "" };

export function CompanySettingsForm({ settings, locale }: { settings: CompanySettings; locale: string }) {
  const ar = locale === "ar";
  const action = updateCompanySettingsAction.bind(null, locale);
  const [state, formAction, pending] = useActionState(action, initialState);
  return (
    <form action={formAction} className="portal-form settings-form">
      <input type="hidden" name="version" value={settings.version} />
      <label>{ar ? "اسم الشركة" : "Company name"}<input name="display_name" defaultValue={settings.display_name} required /></label>
      <label>{ar ? "اللغة الافتراضية" : "Default language"}<select name="default_locale" defaultValue={settings.default_locale}><option value="ar">العربية</option><option value="en">English</option></select></label>
      <label>{ar ? "المنطقة الزمنية" : "Timezone"}<input name="timezone" defaultValue={settings.timezone} required /></label>
      <label>{ar ? "رمز الدولة" : "Country code"}<input name="country_code" defaultValue={settings.country_code} maxLength={2} required /></label>
      <button type="submit" disabled={pending}>{pending ? (ar ? "جارٍ الحفظ..." : "Saving...") : (ar ? "حفظ الإعدادات" : "Save settings")}</button>
      <p className={state.success ? "form-success" : "form-error"} aria-live="polite">{state.message}</p>
    </form>
  );
}
