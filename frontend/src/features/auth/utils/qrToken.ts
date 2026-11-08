/**
 * Extracts the opaque login token from scanned QR content.
 * Accepts either a raw token or a URL carrying it as `?t=` / `?token=` / `#t=`.
 * The token itself is validated ONLY by the backend; this is just a shape check so we
 * don't send random QR codes (e.g. a shop link) to the auth endpoint.
 */
const TOKEN_RE = /^[A-Za-z0-9_\-.~]{16,512}$/;

export function extractQrToken(raw: string): string | null {
  const value = raw.trim();
  if (!value) return null;

  if (/^https?:\/\//i.test(value)) {
    try {
      const url = new URL(value);
      const hash = new URLSearchParams(url.hash.replace(/^#/, ''));
      const candidate = url.searchParams.get('t') ?? url.searchParams.get('token') ?? hash.get('t') ?? hash.get('token');
      return candidate && TOKEN_RE.test(candidate) ? candidate : null;
    } catch {
      return null;
    }
  }

  // Never accept something that looks like a 14-digit JSHSHIR as a token.
  if (/^\d{14}$/.test(value)) return null;
  return TOKEN_RE.test(value) ? value : null;
}

/**
 * The token from a ticket link's fragment: `https://…/qr#t=<token>`. The fragment is never sent to
 * a server (not in requests, logs or Referer), which is why tickets put the token there.
 */
export function readTokenFromHash(hash: string): string | null {
  const params = new URLSearchParams(hash.replace(/^#/, ''));
  const candidate = params.get('t') ?? params.get('token');
  return candidate ? extractQrToken(candidate) : null;
}
