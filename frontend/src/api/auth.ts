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

export interface SignupResponse {
  message: string;
  email: string;
}

/** Creates the account and triggers the OTP email — does not sign the user in. */
export function signup(
  email: string,
  password: string,
): Promise<SignupResponse> {
  return request<SignupResponse>("/auth/signup", {
    method: "POST",
    body: { email, password },
    anonymous: true,
  });
}

/** Verifies the OTP and signs the user in on success. */
export async function verifyOtp(
  email: string,
  otp: string,
): Promise<AuthToken> {
  const token = await request<AuthToken>("/auth/verify-otp", {
    method: "POST",
    body: { email, otp },
    anonymous: true,
  });

  setToken(token.access_token);
  return token;
}

export interface MessageResponse {
  message: string;
}

export function resendOtp(email: string): Promise<MessageResponse> {
  return request<MessageResponse>("/auth/resend-otp", {
    method: "POST",
    body: { email },
    anonymous: true,
  });
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
