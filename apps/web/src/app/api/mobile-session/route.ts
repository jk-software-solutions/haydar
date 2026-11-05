import { NextRequest, NextResponse } from "next/server";

import { apiBaseUrl } from "@/lib/auth/server-session";

/** Bootstrap the web portal cookie jar when it is opened from the Flutter app.
 * The tokens are sent in request headers, never in the URL, and are replaced
 * by the normal HttpOnly web cookies before redirecting to the portal.
 */
export async function GET(request: NextRequest) {
  const authorization = request.headers.get("authorization");
  const accessToken = authorization?.startsWith("Bearer ")
    ? authorization.slice("Bearer ".length).trim()
    : "";
  if (!accessToken) return new NextResponse("Authentication required", { status: 401 });

  const sessionResponse = await fetch(`${apiBaseUrl}/auth/session`, {
    headers: { Authorization: `Bearer ${accessToken}`, Accept: "application/json" },
    cache: "no-store",
  });
  if (!sessionResponse.ok) return new NextResponse("Session expired", { status: 401 });

  const session = (await sessionResponse.json()) as {
    roles?: string[];
  };
  const canEnterPortal = (session.roles ?? []).some((role) =>
    ["OWNER", "MANAGER", "HR_OFFICER", "SUPERVISOR"].includes(role),
  );
  if (!canEnterPortal) return new NextResponse("Portal access denied", { status: 403 });

  // Reverse proxies may expose the Next.js process as 127.0.0.1:3000. Never
  // send that internal origin to the phone; use the configured public origin
  // (or the forwarded host when running behind a proxy in another environment).
  const forwardedProto = request.headers.get("x-forwarded-proto")?.split(",")[0]?.trim();
  const forwardedHost = request.headers.get("x-forwarded-host")?.split(",")[0]?.trim();
  const configuredOrigin = process.env.HAYDAR_WEB_PUBLIC_URL?.trim();
  const origin = configuredOrigin || (
    forwardedHost
      ? `${forwardedProto || request.nextUrl.protocol.replace(":", "")}://${forwardedHost}`
      : request.nextUrl.origin
  );
  const response = NextResponse.redirect(
    new URL(`/${request.nextUrl.searchParams.get("lang") === "en" ? "en" : "ar"}/company`, origin),
  );
  response.cookies.set("haydar_access", accessToken, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 15 * 60,
  });
  const refreshToken = request.headers.get("x-refresh-token")?.trim();
  if (refreshToken) {
    response.cookies.set("haydar_refresh", refreshToken, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: 7 * 24 * 60 * 60,
    });
  }
  return response;
}
