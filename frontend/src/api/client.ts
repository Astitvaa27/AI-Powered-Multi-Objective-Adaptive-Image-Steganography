export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000"
).replace(/\/$/, "");

const TOKEN_STORAGE_KEY = "stegolab.token";

export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;

  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }

  /** True when the session is missing or has expired. */
  get isAuthError(): boolean {
    return this.status === 401;
  }
}

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_STORAGE_KEY, token);
    else localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    /* storage unavailable — the session simply won't persist */
  }
}

type UnauthorizedHandler = () => void;

let onUnauthorized: UnauthorizedHandler | null = null;

export function setUnauthorizedHandler(handler: UnauthorizedHandler | null) {
  onUnauthorized = handler;
}

/**
 * FastAPI returns `detail` as either a string or a list of validation
 * objects. Flatten both shapes into something worth showing a user.
 */
function readDetail(body: unknown, status: number): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;

    if (typeof detail === "string") return detail;

    if (Array.isArray(detail)) {
      const messages = detail
        .map((entry) => {
          if (entry && typeof entry === "object" && "msg" in entry) {
            const loc = "loc" in entry ? (entry as { loc: unknown[] }).loc : [];
            const field = Array.isArray(loc) ? loc.slice(-1)[0] : "";
            return field
              ? `${String(field)}: ${String((entry as { msg: unknown }).msg)}`
              : String((entry as { msg: unknown }).msg);
          }
          return null;
        })
        .filter(Boolean);

      if (messages.length) return messages.join(" · ");
    }
  }

  const fallbacks: Record<number, string> = {
    400: "The request was rejected as invalid.",
    401: "Your session has expired. Please sign in again.",
    403: "You do not have permission to perform this action.",
    404: "The requested resource was not found.",
    409: "That resource already exists.",
    413: "The uploaded file is too large.",
    422: "Some of the supplied values were invalid.",
    500: "The server encountered an internal error.",
    503: "The service is temporarily unavailable.",
  };

  return fallbacks[status] ?? `Request failed with status ${status}.`;
}

interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  /** Send as multipart instead of JSON. */
  formData?: FormData;
  /** Query string parameters. */
  params?: Record<string, string | number | boolean | undefined | null>;
  /** Skip attaching the bearer token. */
  anonymous?: boolean;
}

export async function request<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { body, formData, params, anonymous, headers, ...rest } = options;

  const url = new URL(`${API_BASE_URL}${path}`);

  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, String(value));
      }
    }
  }

  const finalHeaders = new Headers(headers);

  if (!anonymous) {
    const token = getToken();
    if (token) finalHeaders.set("Authorization", `Bearer ${token}`);
  }

  let payload: BodyInit | undefined;

  if (formData) {
    payload = formData;
  } else if (body !== undefined) {
    finalHeaders.set("Content-Type", "application/json");
    payload = JSON.stringify(body);
  }

  let response: Response;

  try {
    response = await fetch(url.toString(), {
      ...rest,
      headers: finalHeaders,
      body: payload,
    });
  } catch {
    throw new ApiError(
      0,
      "Cannot reach the backend. Check that the API server is running and that VITE_API_BASE_URL is correct.",
    );
  }

  if (response.status === 204) return undefined as T;

  const contentType = response.headers.get("content-type") ?? "";
  const isJson = contentType.includes("application/json");
  const parsed = isJson ? await response.json().catch(() => null) : null;

  if (!response.ok) {
    if (response.status === 401 && !anonymous) onUnauthorized?.();

    throw new ApiError(
      response.status,
      readDetail(parsed, response.status),
      parsed,
    );
  }

  return parsed as T;
}

/** Authenticated blob fetch, used for image previews. */
export async function requestBlob(path: string): Promise<string> {
  const headers = new Headers();
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, { headers });
  } catch {
    throw new ApiError(0, "Cannot reach the backend to load this image.");
  }

  if (!response.ok) {
    if (response.status === 401) onUnauthorized?.();
    throw new ApiError(response.status, readDetail(null, response.status));
  }

  return URL.createObjectURL(await response.blob());
}

/** Authenticated file download — triggers a browser save dialog. */
export async function downloadFile(
  path: string,
  filename: string,
): Promise<void> {
  const headers = new Headers();
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, { headers });
  } catch {
    throw new ApiError(0, "Cannot reach the backend to download this file.");
  }

  if (!response.ok) {
    if (response.status === 401) onUnauthorized?.();
    throw new ApiError(response.status, readDetail(null, response.status));
  }

  const url = URL.createObjectURL(await response.blob());

  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();

  // Revoke on the next tick so the click has already been handled.
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}