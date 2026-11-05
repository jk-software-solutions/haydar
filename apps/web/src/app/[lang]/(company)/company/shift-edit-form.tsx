"use client";

import { useActionState } from "react";

import { updateShiftAction, type OrganizationActionState } from "./actions";

const initialState: OrganizationActionState = { message: "" };

export type EditableShift = {
  id: string;
  code: string;
  name: string;
  start_time: string;
  end_time: string;
  working_days: number[];
  grace_period_minutes: number;
  break_duration_minutes: number;
  effective_from: string;
  effective_to: string | null;
  recurrence?: {
    location_policy?: string;
    periods?: { start_time?: string; end_time?: string }[];
    checkout_grace_period_minutes?: number;
  };
  is_active: boolean;
  version: number;
};

export function ShiftEditForm({ locale, shift }: { locale: string; shift: EditableShift }) {
  const ar = locale === "ar";
  const [state, formAction, pending] = useActionState(
    updateShiftAction.bind(null, locale, shift.id),
    initialState,
  );
  const periods = shift.recurrence?.periods ?? [];
  const secondPeriod = periods[1];
  const locationPolicy = shift.recurrence?.location_policy ?? "branch_required";
  const checkoutGrace = shift.recurrence?.checkout_grace_period_minutes ?? 15;
  const dayLabels = ar
    ? ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
    : ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

  return (
    <details className="operation-form-card">
      <summary>{ar ? "تفاصيل وتعديل الوردية" : "Shift details and edit"}</summary>
      <form action={formAction} className="portal-form shift-form">
        <input type="hidden" name="version" value={shift.version} />
        <label>{ar ? "رمز الوردية" : "Shift code"}<input name="code" defaultValue={shift.code} required /></label>
        <label>{ar ? "اسم الوردية" : "Shift name"}<input name="name" defaultValue={shift.name} required /></label>
        <label>{ar ? "وقت البداية" : "Start time"}<input name="start_time" type="time" defaultValue={shift.start_time.slice(0, 5)} required /></label>
        <label>{ar ? "وقت النهاية" : "End time"}<input name="end_time" type="time" defaultValue={shift.end_time.slice(0, 5)} required /></label>
        <label>{ar ? "بداية الدوام الثاني (اختياري)" : "Second period start (optional)"}<input name="second_start_time" type="time" defaultValue={secondPeriod?.start_time?.slice(0, 5) ?? ""} /></label>
        <label>{ar ? "نهاية الدوام الثاني (اختياري)" : "Second period end (optional)"}<input name="second_end_time" type="time" defaultValue={secondPeriod?.end_time?.slice(0, 5) ?? ""} /></label>
        <label>
          {ar ? "سياسة الموقع" : "Location policy"}
          <select name="location_policy" defaultValue={locationPolicy}>
            <option value="branch_required">{ar ? "يتطلب موقع الفرع" : "Branch location required"}</option>
            <option value="location_not_required">{ar ? "لا يعتمد على موقع الموظف" : "Does not depend on employee location"}</option>
          </select>
        </label>
        <label>{ar ? "فترة السماح بالدقائق" : "Grace minutes"}<input name="grace_period_minutes" type="number" min="0" max="240" defaultValue={shift.grace_period_minutes} required /></label>
        <label>{ar ? "مهلة إثبات الانصراف بعد نهاية الوردية (دقائق)" : "Check-out grace after shift (minutes)"}<input name="checkout_grace_period_minutes" type="number" min="0" max="240" defaultValue={checkoutGrace} required /></label>
        <label>{ar ? "مدة الاستراحة بالدقائق" : "Break minutes"}<input name="break_duration_minutes" type="number" min="0" max="720" defaultValue={shift.break_duration_minutes} required /></label>
        <label>{ar ? "سارية من" : "Effective from"}<input name="effective_from" type="date" defaultValue={shift.effective_from} required /></label>
        <label>{ar ? "سارية حتى" : "Effective to"}<input name="effective_to" type="date" defaultValue={shift.effective_to ?? ""} /></label>
        <label>
          {ar ? "حالة الوردية" : "Shift status"}
          <select name="is_active" defaultValue={shift.is_active ? "true" : "false"}>
            <option value="true">{ar ? "نشطة" : "Active"}</option>
            <option value="false">{ar ? "غير نشطة" : "Inactive"}</option>
          </select>
        </label>
        <fieldset className="weekday-field">
          <legend>{ar ? "أيام العمل" : "Working days"}</legend>
          {dayLabels.map((label, day) => (
            <label key={day}>
              <input type="checkbox" name="working_days" value={day} defaultChecked={shift.working_days.includes(day)} />
              {label}
            </label>
          ))}
        </fieldset>
        <button type="submit" disabled={pending}>{pending ? (ar ? "جارٍ الحفظ..." : "Saving...") : (ar ? "حفظ الوردية" : "Save shift")}</button>
        <p className={state.success ? "form-success" : "form-error"} aria-live="polite">{state.message}</p>
      </form>
    </details>
  );
}
