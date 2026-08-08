import "server-only";

import { cookies } from "next/headers";

const accessCookie = "haydar_access";
const refreshCookie = "haydar_refresh";

export type WebSession = {
  user: { id: string; email: string; full_name: string };
  company: { id: string; display_name: string };
  membership_id: string;
  roles: string[];
  permissions: string[];
  scope: {
    unrestricted: boolean;
    branch_ids: string[];
    department_ids: string[];
    group_ids: string[];
  };
};

type TokenResponse = {
  access_token: string;
  refresh_token: string;
  expires_in_seconds: number;
  session: WebSession;
};

export type RegisterCompanyInput = {
  company_name: string;
  owner_full_name: string;
  owner_email: string;
  password: string;
};

export type ApiProblem = {
  code?: string;
  detail?: string;
};

export const apiBaseUrl =
  process.env.HAYDAR_API_URL ?? "http://127.0.0.1:8000/api/v1";

async function readProblem(response: Response): Promise<ApiProblem> {
  try {
    return (await response.json()) as ApiProblem;
  } catch {
    return {};
  }
}

export async function loginWithApi(identifier: string, password: string): Promise<WebSession> {
  const response = await fetch(`${apiBaseUrl}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ identifier, password }),
    cache: "no-store",
  });
  if (!response.ok) {
    const problem = await readProblem(response);
    throw new Error(problem.detail ?? "Authentication failed.");
  }
  const payload = (await response.json()) as TokenResponse;
  return persistTokenResponse(payload);
}

export async function registerCompanyWithApi(input: RegisterCompanyInput): Promise<WebSession> {
  const response = await fetch(`${apiBaseUrl}/auth/register-company`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(input),
    cache: "no-store",
  });
  if (!response.ok) {
    const problem = await readProblem(response);
    throw new Error(problem.detail ?? "Company registration failed.");
  }
  return persistTokenResponse((await response.json()) as TokenResponse);
}

async function persistTokenResponse(payload: TokenResponse): Promise<WebSession> {
  const cookieStore = await cookies();
  const common = {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax" as const,
    path: "/",
  };
  cookieStore.set(accessCookie, payload.access_token, {
    ...common,
    maxAge: payload.expires_in_seconds,
  });
  cookieStore.set(refreshCookie, payload.refresh_token, {
    ...common,
    maxAge: 60 * 60 * 24 * 7,
  });
  return payload.session;
}

export async function getAccessToken(): Promise<string | null> {
  return (await cookies()).get(accessCookie)?.value ?? null;
}

export async function getWebSession(): Promise<WebSession | null> {
  const accessToken = await getAccessToken();
  if (!accessToken) return null;
  const response = await fetch(`${apiBaseUrl}/auth/session`, {
    headers: { Authorization: `Bearer ${accessToken}`, Accept: "application/json" },
    cache: "no-store",
  });
  if (!response.ok) return null;
  return (await response.json()) as WebSession;
}

export async function logoutWithApi(): Promise<void> {
  const cookieStore = await cookies();
  const refreshToken = cookieStore.get(refreshCookie)?.value;
  try {
    if (refreshToken) {
      await fetch(`${apiBaseUrl}/auth/logout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
        cache: "no-store",
      });
    }
  } finally {
    cookieStore.delete(accessCookie);
    cookieStore.delete(refreshCookie);
  }
}

export async function authorizedApiFetch(path: string, init?: RequestInit): Promise<Response> {
  const accessToken = await getAccessToken();
  if (!accessToken) return new Response(null, { status: 401 });
  const headers = new Headers(init?.headers);
  headers.set("Authorization", `Bearer ${accessToken}`);
  headers.set("Accept", "application/json");
  return fetch(`${apiBaseUrl}${path}`, { ...init, headers, cache: "no-store" });
}
