import { apiBaseUrl, getAccessToken } from "@/lib/auth/server-session";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ fileId: string }> },
) {
  const token = await getAccessToken();
  if (!token) return new Response(null, { status: 401 });
  const { fileId } = await params;
  const upstream = await fetch(`${apiBaseUrl}/files/${fileId}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!upstream.ok) return new Response(null, { status: upstream.status });
  const contentType = upstream.headers.get("Content-Type") ?? "application/octet-stream";
  return new Response(upstream.body, {
    status: 200,
    headers: {
      "Content-Type": contentType,
      "Content-Disposition": contentType.startsWith("image/")
        ? "inline"
        : upstream.headers.get("Content-Disposition") ?? "attachment",
      "Cache-Control": "private, no-store",
      "X-Content-Type-Options": "nosniff",
    },
  });
}
