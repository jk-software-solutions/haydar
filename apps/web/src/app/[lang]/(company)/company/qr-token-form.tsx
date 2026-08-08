"use client";

import { useActionState } from "react";

import { createQrTokenAction, type QrTokenState } from "./operations-actions";

export function QrTokenForm({ locale, branches }: { locale: string; branches: { id: string; name: string }[] }) {
  const ar = locale === "ar";
  const action = createQrTokenAction.bind(null, locale);
  const [state, submit, pending] = useActionState<QrTokenState, FormData>(action, {});
  return <div className="operation-form-card"><form action={submit} className="portal-form inline"><select name="branch_id" required><option value="">{ar ? "اختر الفرع" : "Select branch"}</option>{branches.map((branch) => <option key={branch.id} value={branch.id}>{branch.name}</option>)}</select><input name="valid_for_seconds" type="number" min="30" max="900" defaultValue="120" /><button type="submit" disabled={pending}>{pending ? (ar ? "جارٍ الإنشاء…" : "Creating…") : (ar ? "إنشاء رمز QR" : "Create QR token")}</button></form>{state.token && <div className="activation-token"><strong>{ar ? "رمز مؤقت للفرع" : "Temporary branch token"}</strong><code>{state.token}</code><small>{ar ? "ينتهي" : "Expires"}: {state.expiresAt}</small></div>}{state.message && <p className="form-error">{state.message}</p>}</div>;
}
