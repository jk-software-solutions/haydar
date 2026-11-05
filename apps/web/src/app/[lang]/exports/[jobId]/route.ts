import { apiBaseUrl, getAccessToken } from "@/lib/auth/server-session";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ lang: string; jobId: string }> },
) {
  const token = await getAccessToken();
  if (!token) return new Response(null, { status: 401 });

  const { lang, jobId } = await params;
  let upstream: Response;
  try {
    upstream = await fetch(`${apiBaseUrl}/reports/exports/${jobId}/download`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
  } catch {
    return readableExportError(lang === "ar", 502);
  }

  if (!upstream.ok) return readableExportError(lang === "ar", upstream.status);

  return new Response(upstream.body, {
    status: 200,
    headers: {
      "Content-Type": upstream.headers.get("Content-Type") ?? "application/octet-stream",
      "Content-Disposition": upstream.headers.get("Content-Disposition") ?? "attachment",
    },
  });
}

function readableExportError(arabic: boolean, status: number): Response {
  const expired = status === 410;
  const title = expired
    ? (arabic ? "انتهت صلاحية التقرير" : "Report expired")
    : (arabic ? "تعذر فتح التقرير" : "Could not open report");
  const message = expired
    ? (arabic ? "انتهت مدة الاحتفاظ بهذا الملف. أنشئ تقريرًا جديدًا من صفحة التقارير." : "This file has expired. Create a new report from the Reports page.")
    : (arabic ? "لم يتم العثور على التقرير أو لا تملك صلاحية فتحه." : "The report was not found or you do not have permission to open it.");
  const retry = arabic ? "العودة إلى التقارير" : "Back to reports";
  return new Response(
    `<!doctype html><html lang="${arabic ? "ar" : "en"}" dir="${arabic ? "rtl" : "ltr"}"><meta charset="utf-8"><title>${title}</title><style>body{font-family:system-ui,sans-serif;background:#f3f8f7;color:#173330;display:grid;place-items:center;min-height:100vh;margin:0}.card{max-width:520px;background:#fff;border:1px solid #c8dedb;border-radius:18px;padding:32px;text-align:center;box-shadow:0 12px 32px #0b514218}h1{color:#075f59;font-size:24px}p{line-height:1.7;color:#4f6b68}a{display:inline-block;margin-top:16px;padding:12px 22px;border-radius:10px;background:#075f59;color:#fff;text-decoration:none}</style><main class="card"><h1>${title}</h1><p>${message}</p><a href="/${arabic ? "ar" : "en"}/company?tab=reports">${retry}</a></main></html>`,
    { status, headers: { "Content-Type": "text/html; charset=utf-8" } },
  );
}
