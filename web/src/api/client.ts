const BASE_URL = '/api/v1';

// ── API Error ────────────────────────────────────────────────────

export interface APIErrorBody {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public body?: unknown,
    public code?: string,
  ) {
    const errorMessage = (body as APIErrorBody)?.error?.message || statusText;
    super(`API Error ${status}: ${errorMessage}`);
    this.name = 'ApiError';
    this.code = (body as APIErrorBody)?.error?.code;
  }

  get isAuthError(): boolean {
    return this.status === 401;
  }

  get isRateLimited(): boolean {
    return this.status === 429;
  }

  get userMessage(): string {
    const body = this.body as APIErrorBody | undefined;
    return body?.error?.message || this.statusText;
  }
}

// ── API Key management ───────────────────────────────────────────

let _apiKey: string | null = null;

export function setApiKey(key: string | null): void {
  _apiKey = key;
}

export function getApiKey(): string | null {
  return _apiKey;
}

// ── Response handling ────────────────────────────────────────────

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

function buildQuery(params: Record<string, unknown>): string {
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) {
      searchParams.set(key, String(value));
    }
  }
  const qs = searchParams.toString();
  return qs ? `?${qs}` : '';
}

function buildHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (_apiKey) {
    headers['X-API-Key'] = _apiKey;
  }
  return headers;
}

// ── Retry logic ──────────────────────────────────────────────────

async function fetchWithRetry(
  url: string,
  options: RequestInit,
  maxRetries = 2,
): Promise<Response> {
  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const response = await fetch(url, options);

      // Don't retry client errors (4xx), only server errors (5xx)
      if (response.status < 500 || attempt === maxRetries) {
        return response;
      }

      lastError = new Error(`Server error ${response.status}`);
    } catch (err) {
      lastError = err as Error;
      if (attempt === maxRetries) break;
    }

    // Exponential backoff: 1s, 2s
    await new Promise((resolve) => setTimeout(resolve, 1000 * (attempt + 1)));
  }

  throw lastError || new Error('Request failed');
}

// ── API Client ───────────────────────────────────────────────────

export const apiClient = {
  async get<T>(path: string, params: Record<string, unknown> = {}): Promise<T> {
    const url = `${BASE_URL}${path}${buildQuery(params)}`;
    const response = await fetchWithRetry(url, {
      method: 'GET',
      headers: buildHeaders(),
    });
    return handleResponse<T>(response);
  },

  async post<T>(path: string, body?: unknown): Promise<T> {
    const url = `${BASE_URL}${path}`;
    const response = await fetchWithRetry(url, {
      method: 'POST',
      headers: buildHeaders(),
      body: body ? JSON.stringify(body) : undefined,
    });
    return handleResponse<T>(response);
  },
};

export default apiClient;
