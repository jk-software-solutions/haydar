"use client";

import { useActionState } from "react";

import { updateCompanySettingsAction, type OrganizationActionState } from "./actions";

export type CompanySettings = {
  display_name: string;
  commercial_registration_number: string | null;
  unified_number: string | null;
  contact_phone: string | null;
  tax_number: string | null;
  logo_file_id: string | null;
  default_locale: string;
  timezone: string;
  country_code: string;
  attendance_biometric_policy: "disabled" | "optional" | "required";
  version: number;
};

const initialState: OrganizationActionState = { message: "" };

export function CompanySettingsForm({ settings, locale }: { settings: CompanySettings; locale: string }) {
  const ar = locale === "ar";
  const action = updateCompanySettingsAction.bind(null, locale);
  const [state, formAction, pending] = useActionState(action, initialState);
  return (
    <form action={formAction} encType="multipart/form-data" className="portal-form settings-form">
      <input type="hidden" name="version" value={settings.version} />
      <label>{ar ? "اسم الشركة" : "Company name"}<input name="display_name" defaultValue={settings.display_name} required /></label>
      <label>{ar ? "رقم السجل التجاري" : "Commercial registration number"}<input name="commercial_registration_number" defaultValue={settings.commercial_registration_number ?? ""} /></label>
      <label>{ar ? "الرقم الموحد" : "Unified number"}<input name="unified_number" defaultValue={settings.unified_number ?? ""} /></label>
      <label>{ar ? "جوال الشركة (اختياري)" : "Company phone (optional)"}<input name="contact_phone" defaultValue={settings.contact_phone ?? ""} inputMode="tel" /></label>
      <label>{ar ? "الرقم الضريبي (اختياري)" : "Tax number (optional)"}<input name="tax_number" defaultValue={settings.tax_number ?? ""} /></label>
      <label>
        {ar ? "شعار الشركة للتقارير (PNG أو JPG)" : "Company logo for reports (PNG or JPG)"}
        <input name="logo" type="file" accept="image/png,image/jpeg,image/webp" />
        <small>{settings.logo_file_id ? (ar ? "يوجد شعار محفوظ ومعروض أدناه؛ خانة اختيار الملف تُفرغ تلقائياً بعد الحفظ لأسباب أمنية. ارفع صورة جديدة لاستبداله." : "A logo is saved and shown below. The file picker clears after saving for security; upload a new image to replace it.") : (ar ? "يظهر الشعار تلقائياً في ملفات PDF." : "The logo appears automatically in PDF reports.")}</small>
        {settings.logo_file_id && (
          <img
            className="company-logo-preview"
            src={`/api/files/${settings.logo_file_id}`}
            alt={ar ? "شعار الشركة المحفوظ" : "Saved company logo"}
          />
        )}
      </label>
      <label>{ar ? "اللغة الافتراضية" : "Default language"}<select name="default_locale" defaultValue={settings.default_locale}><option value="ar">العربية</option><option value="en">English</option></select></label>
      <label>{ar ? "المنطقة الزمنية" : "Timezone"}<input name="timezone" defaultValue={settings.timezone} required /></label>
      <label>{ar ? "رمز الدولة" : "Country code"}<input name="country_code" defaultValue={settings.country_code} maxLength={2} required /></label>
      <label>
        {ar ? "سياسة تأكيد الحضور بالبصمة" : "Attendance biometric policy"}
        <select name="attendance_biometric_policy" defaultValue={settings.attendance_biometric_policy}>
          <option value="disabled">{ar ? "معطلة" : "Disabled"}</option>
          <option value="optional">{ar ? "اختيارية عند توفرها" : "Optional when available"}</option>
          <option value="required">{ar ? "مطلوبة" : "Required"}</option>
        </select>
        <small>{ar ? "البصمة تحقق محلي على الجهاز المعتمد وليست إثباتاً مشفراً للخادم." : "Biometrics are checked locally on the approved device; the server declaration is not cryptographic attestation."}</small>
      </label>
      <button type="submit" disabled={pending}>{pending ? (ar ? "جارٍ الحفظ..." : "Saving...") : (ar ? "حفظ الإعدادات" : "Save settings")}</button>
      <p className={state.success ? "form-success" : "form-error"} aria-live="polite">{state.message}</p>
    </form>
  );
}
