"use client";

import { useActionState } from "react";

import {
  createQrTokenAction,
  revokeQrTokenAction,
  type QrTokenState,
} from "./operations-actions";

export function QrTokenForm({ locale, branches }: { locale: string; branches: { id: string; name: string }[] }) {
  const ar = locale === "ar";
  const [state, submit, pending] = useActionState<QrTokenState, FormData>(
    createQrTokenAction.bind(null, locale),
    {},
  );
  const qrImageUrl = state.token
    ? `https://api.qrserver.com/v1/create-qr-code/?size=220x220&margin=12&data=${encodeURIComponent(state.token)}`
    : "";
  return (
    <div className="operation-form-card">
      <form action={submit} className="portal-form inline">
        <select name="branch_id" required>
          <option value="">{ar ? "اختر الفرع" : "Select branch"}</option>
          {branches.map((branch) => <option key={branch.id} value={branch.id}>{branch.name}</option>)}
        </select>
        <input name="valid_for_seconds" type="number" min="30" max="900" defaultValue="120" />
        <button type="submit" name="rotate" value="false" disabled={pending}>
          {pending ? (ar ? "جارٍ الإنشاء…" : "Creating…") : (ar ? "إنشاء رمز QR" : "Create QR token")}
        </button>
        <button type="submit" name="rotate" value="true" disabled={pending}>
          {ar ? "تدوير وإبطال الرموز السابقة" : "Rotate and revoke previous"}
        </button>
      </form>
      {state.token && (
        <div className="activation-token">
          <strong>{ar ? "رمز QR مؤقت للفرع" : "Temporary branch QR code"}</strong>
          <img className="qr-code-preview" src={qrImageUrl} alt={ar ? "رمز QR للحضور" : "Attendance QR code"} />
          <small>
            {ar
              ? "يعرضه المدير في الفرع، ثم يمسحه الموظف من تطبيق حاضر لتسجيل الحضور أو الانصراف."
              : "Show this at the branch; employees scan it in the Hadir app to check in or out."}
          </small>
          <code>{state.token}</code>
          <small>{ar ? "الرمز النصي احتياطي عند تعذر قراءة QR." : "The text token is a fallback if QR scanning is unavailable."}</small>
          <small>{ar ? "ينتهي" : "Expires"}: {state.expiresAt}</small>
          {state.tokenId && (
            <form action={revokeQrTokenAction.bind(null, locale, state.tokenId)}>
              <button type="submit" className="danger-button">{ar ? "إبطال الرمز" : "Revoke token"}</button>
            </form>
          )}
        </div>
      )}
      {state.message && <p className="form-error">{state.message}</p>}
    </div>
  );
}
