import axios, { AxiosError, type AxiosRequestConfig } from 'axios';
import type { z } from 'zod';
import { env } from '@/app/config/env';

/**
 * Single axios instance for the whole app.
 * Sessions are carried by HttpOnly cookies set by the backend — the frontend never
 * reads, stores or attaches auth tokens itself.
 */
export const http = axios.create({
  baseURL: env.apiBaseUrl,
  withCredentials: true,
  timeout: 15_000,
  headers: { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
});

export type ApiErrorKind = 'network' | 'unauthorized' | 'forbidden' | 'not_found' | 'conflict' | 'validation' | 'rate_limited' | 'server' | 'invalid_response' | 'unknown';

/** Normalised error shape used by every feature. Never contains request bodies (may hold JSHSHIR). */
export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number | null;
  /** Machine-readable backend code, e.g. `QR_EXPIRED`. */
  readonly code: string | null;

  constructor(kind: ApiErrorKind, status: number | null, code: string | null, message: string) {
    super(message);
    this.name = 'ApiError';
    this.kind = kind;
    this.status = status;
    this.code = code;
  }

  get isRetryable(): boolean {
    return this.kind === 'network' || this.kind === 'server' || this.kind === 'rate_limited';
  }
}

function kindFromStatus(status: number): ApiErrorKind {
  if (status === 401) return 'unauthorized';
  if (status === 403) return 'forbidden';
  if (status === 404) return 'not_found';
  if (status === 409) return 'conflict';
  if (status === 422 || status === 400) return 'validation';
  if (status === 429) return 'rate_limited';
  if (status >= 500) return 'server';
  return 'unknown';
}

export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;
  if (error instanceof AxiosError) {
    if (!error.response) {
      return new ApiError('network', null, error.code ?? null, 'Network error');
    }
    const status = error.response.status;
    const data = error.response.data as { code?: unknown; message?: unknown } | undefined;
    const code = typeof data?.code === 'string' ? data.code : null;
    const message = typeof data?.message === 'string' ? data.message : `HTTP ${status}`;
    return new ApiError(kindFromStatus(status), status, code, message);
  }
  return new ApiError('unknown', null, null, error instanceof Error ? error.message : 'Unknown error');
}

/* ---------- global 401 handling ---------- */
type UnauthorizedListener = () => void;
let onUnauthorized: UnauthorizedListener | null = null;
export function setUnauthorizedHandler(listener: UnauthorizedListener | null): void {
  onUnauthorized = listener;
}

const AUTH_PATHS = ['/auth/me', '/auth/jshshir', '/auth/qr', '/auth/logout'];

http.interceptors.response.use(undefined, (error: unknown) => {
  const apiError = toApiError(error);
  const url = error instanceof AxiosError ? (error.config?.url ?? '') : '';
  if (apiError.kind === 'unauthorized' && !AUTH_PATHS.some((p) => url.startsWith(p))) {
    onUnauthorized?.();
  }
  return Promise.reject(apiError);
});

/**
 * Typed request helper: performs the call and validates the response shape with zod,
 * so wrong backend assumptions fail loudly instead of rendering garbage.
 */
export async function request<S extends z.ZodType>(schema: S, config: AxiosRequestConfig): Promise<z.infer<S>> {
  const response = await http.request<unknown>(config);
  const parsed = schema.safeParse(response.data);
  if (!parsed.success) {
    if (env.isDev) console.error('[api] Unexpected response shape', config.url, parsed.error.issues);
    throw new ApiError('invalid_response', response.status, null, 'Unexpected response shape');
  }
  return parsed.data;
}
