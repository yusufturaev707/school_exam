/** Only allow same-app relative paths as post-login redirect targets (prevents open redirects). */
export function safeRedirect(state: unknown): string {
  const from = (state as { from?: unknown } | null)?.from;
  if (typeof from === 'string' && from.startsWith('/') && !from.startsWith('//') && !from.startsWith('/login')) return from;
  return '/';
}
