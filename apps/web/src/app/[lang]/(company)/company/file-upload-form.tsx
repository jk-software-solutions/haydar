"use client";

import { useActionState } from "react";

import { uploadFileAction, type FileUploadState } from "./operations-actions";

const initialState: FileUploadState = {};

export function FileUploadForm({ locale }: { locale: string }) {
  const ar = locale === "ar";
  const [state, action, pending] = useActionState(uploadFileAction, initialState);
  return (
    <form action={action} className="portal-form operation-form">
      <input
        name="upload"
        type="file"
        required
        accept=".pdf,.jpg,.jpeg,.png,.webp,.txt,.docx,.xlsx"
      />
      <button type="submit" disabled={pending}>
        {pending ? (ar ? "جارٍ الرفع..." : "Uploading...") : ar ? "رفع ملف محمي" : "Upload protected file"}
      </button>
      {state.fileId && (
        <p role="status">
          {ar ? "تم الرفع" : "Uploaded"}: {state.filename} · <code>{state.fileId}</code>
        </p>
      )}
      {state.message && <p role="alert">{state.message}</p>}
    </form>
  );
}
