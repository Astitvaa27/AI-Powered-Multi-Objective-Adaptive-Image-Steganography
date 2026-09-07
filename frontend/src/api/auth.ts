import { request, setToken } from "./client";
import type { AuthToken } from "./types";

/**
 * The backend's /auth/login declares email and password as query
 * parameters, so they are sent that way rather than as a JSON body.
 */
export async function login(
  email: string,
  password: string,
): Promise<AuthToken> {
  const token = await request<AuthToken>("/auth/login", {
    method: "POST",
    params: { email, password },
    anonymous: true,
  });

  setToken(token.access_token);
  return token;
}

export function logout(): void {
  setToken(null);
}

export interface HealthStatus {
  status: string;
  environment?: string;
}

export function checkHealth(): Promise<HealthStatus> {
  return request<HealthStatus>("/health", { anonymous: true });
}

export function checkDatabaseHealth(): Promise<{
  status: string;
  database: string;
}> {
  return request("/health/db", { anonymous: true });
}
