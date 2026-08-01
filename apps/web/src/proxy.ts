import { NextRequest, NextResponse } from "next/server";

import { hasLocale, preferredLocale } from "@/i18n/locales";

const apiBaseUrl = process.env.HAYDAR_API_URL ?? "http://127.0.0.1:8000/api/v1";

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const firstSegment = pathname.split("/")[1];
  const accessToken = request.cookies.get("haydar_access")?.value;
  const refreshToken = request.cookies.get("haydar_refresh")?.value;

  let refreshed: { access_token: string; refresh_token: string; expires_in_seconds: number } | null = null;
  let refreshFailed = false;
  if (!accessToken && refreshToken) {
    try {
      const response = await fetch(`${apiBaseUrl}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
        cache: "no-store",
      });
      if (response.ok) {
        refreshed = await response.json();
        request.cookies.set("haydar_access", refreshed!.access_token);
        request.cookies.set("haydar_refresh", refreshed!.refresh_token);
      } else {
        refreshFailed = true;
      }
    } catch {
      refreshed = null;
      refreshFailed = true;
    }
  }

  let nextResponse: NextResponse;
  if (hasLocale(firstSegment)) {
    nextResponse = NextResponse.next({ request });
  } else {
    const locale = preferredLocale(request.headers.get("accept-language"));
    const destination = request.nextUrl.clone();
    destination.pathname = `/${locale}${pathname === "/" ? "" : pathname}`;
    nextResponse = NextResponse.redirect(destination);
  }
  if (refreshed) {
    const common = {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax" as const,
      path: "/",
    };
    nextResponse.cookies.set("haydar_access", refreshed.access_token, {
      ...common,
      maxAge: refreshed.expires_in_seconds,
    });
    nextResponse.cookies.set("haydar_refresh", refreshed.refresh_token, {
      ...common,
      maxAge: 60 * 60 * 24 * 7,
    });
  } else if (refreshFailed) {
    nextResponse.cookies.delete("haydar_access");
    nextResponse.cookies.delete("haydar_refresh");
  }
  return nextResponse;
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|.*\\..*).*)"],
};
