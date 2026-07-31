import { NextRequest, NextResponse } from "next/server";

import { hasLocale, preferredLocale } from "@/i18n/locales";

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const firstSegment = pathname.split("/")[1];

  if (hasLocale(firstSegment)) {
    return NextResponse.next();
  }

  const locale = preferredLocale(request.headers.get("accept-language"));
  const destination = request.nextUrl.clone();
  destination.pathname = `/${locale}${pathname === "/" ? "" : pathname}`;
  return NextResponse.redirect(destination);
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|.*\\..*).*)"],
};
