/** Centralised, typed access to build-time configuration. */
export const env = {
  apiBaseUrl: (import.meta.env.VITE_API_BASE_URL as string | undefined) || '/api',
  useMocks: import.meta.env.VITE_USE_MOCKS === 'true',
  isDev: import.meta.env.DEV,
} as const;
