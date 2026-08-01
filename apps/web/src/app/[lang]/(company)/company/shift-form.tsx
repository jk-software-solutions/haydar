"use client";

import { useActionState } from "react";

import { createShiftAction, type OrganizationActionState } from "./actions";

const initialState: OrganizationActionState = { message: "" };

export function ShiftForm({ locale }: { locale: string }) {
  const ar = locale === "ar";
  const action = createShiftAction.bind(null, locale);
  const [state, formAction, pending] = useActionState(action, initialState);
  const dayLabels = ar ? ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"] : ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  return (
    <form action={formAction} className="portal-form shift-form">
      <label>{ar ? "رمز الوردية" : "Shift code"}<input name="code" required /></label>
      <label>{ar ? "اسم الوردية" : "Shift name"}<input name="name" required /></label>
      <label>{ar ? "وقت البداية" : "Start time"}<input name="start_time" type="time" required /></label>
      <label>{ar ? "وقت النهاية" : "End time"}<input name="end_time" type="time" required /></label>
      <label>{ar ? "فترة السماح بالدقائق" : "Grace minutes"}<input name="grace_period_minutes" type="number" min="0" max="240" defaultValue="0" required /></label>
      <label>{ar ? "مدة الاستراحة بالدقائق" : "Break minutes"}<input name="break_duration_minutes" type="number" min="0" max="720" defaultValue="0" required /></label>
      <label>{ar ? "سارية من" : "Effective from"}<input name="effective_from" type="date" required /></label>
      <label>{ar ? "سارية حتى" : "Effective to"}<input name="effective_to" type="date" /></label>
      <fieldset className="weekday-field"><legend>{ar ? "أيام العمل" : "Working days"}</legend>{dayLabels.map((label, day) => <label key={day}><input type="checkbox" name="working_days" value={day} />{label}</label>)}</fieldset>
      <button type="submit" disabled={pending}>{pending ? (ar ? "جارٍ الإنشاء..." : "Creating...") : (ar ? "إضافة الوردية" : "Add shift")}</button>
      <p className={state.success ? "form-success" : "form-error"} aria-live="polite">{state.message}</p>
    </form>
  );
}
