const BASE_URL = "/api/v1";

// ── API Error ────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public body?: unknown,
  ) {
    const msg =
      (body as { error?: { message?: string } })?.error?.message || statusText;
    super(`API Error ${status}: ${msg}`);
    this.name = "ApiError";
  }
}

// ── API Key ──────────────────────────────────────────────────────

let _apiKey: string | null = null;

export function setApiKey(key: string | null): void {
  _apiKey = key;
}

// ── Response Handling ────────────────────────────────────────────

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let body: unknown;
    try {
      body = await response.json();
    } catch {
      body = await response.text();
    }
    throw new ApiError(response.status, response.statusText, body);
  }
  return response.json() as Promise<T>;
}

function buildHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (_apiKey) {
    headers["X-API-Key"] = _apiKey;
  }
  return headers;
}

function buildQuery(params: Record<string, unknown>): string {
  const sp = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) {
      sp.set(key, String(value));
    }
  }
  const qs = sp.toString();
  return qs ? `?${qs}` : "";
}

// ── Retry Logic ──────────────────────────────────────────────────

async function fetchWithRetry(
  url: string,
  options: RequestInit,
  maxRetries = 2,
): Promise<Response> {
  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const response = await fetch(url, options);
      if (response.status < 500 || attempt === maxRetries) {
        return response;
      }
      lastError = new Error(`Server error ${response.status}`);
    } catch (err) {
      lastError = err as Error;
      if (attempt === maxRetries) break;
    }
    await new Promise((r) => setTimeout(r, 1000 * (attempt + 1)));
  }

  throw lastError ?? new Error("Request failed");
}

// ── API Client ───────────────────────────────────────────────────

export const apiClient = {
  async get<T>(
    path: string,
    params: Record<string, unknown> = {},
  ): Promise<T> {
    const url = `${BASE_URL}${path}${buildQuery(params)}`;
    const response = await fetchWithRetry(url, {
      method: "GET",
      headers: buildHeaders(),
    });
    return handleResponse<T>(response);
  },

  async post<T>(path: string, body?: unknown): Promise<T> {
    const url = `${BASE_URL}${path}`;
    const response = await fetchWithRetry(url, {
      method: "POST",
      headers: buildHeaders(),
      body: body ? JSON.stringify(body) : undefined,
    });
    return handleResponse<T>(response);
  },

  async getBlob(
    path: string,
    params: Record<string, unknown> = {},
  ): Promise<{ blob: Blob; headers: Headers }> {
    const url = `${BASE_URL}${path}${buildQuery(params)}`;
    const response = await fetchWithRetry(url, {
      method: "GET",
      headers: _apiKey ? { "X-API-Key": _apiKey } : {},
    });
    if (!response.ok) {
      throw new ApiError(response.status, response.statusText);
    }
    return { blob: await response.blob(), headers: response.headers };
  },
};
