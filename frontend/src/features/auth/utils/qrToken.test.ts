import { describe, expect, it } from 'vitest';
import { extractQrToken, readTokenFromHash } from './qrToken';

describe('extractQrToken', () => {
  it('accepts a raw opaque token', () => {
    expect(extractQrToken('  k3J9xQ2m_Lp8-ZtR4vW7yB1c  ')).toBe('k3J9xQ2m_Lp8-ZtR4vW7yB1c');
  });
  it('reads the token from a URL query or hash', () => {
    expect(extractQrToken('https://exam.example.uz/qr?t=k3J9xQ2m_Lp8-ZtR4vW7yB1c')).toBe('k3J9xQ2m_Lp8-ZtR4vW7yB1c');
    expect(extractQrToken('https://exam.example.uz/qr#token=k3J9xQ2m_Lp8-ZtR4vW7yB1c')).toBe('k3J9xQ2m_Lp8-ZtR4vW7yB1c');
  });
  it('rejects short, foreign or JSHSHIR-like content', () => {
    expect(extractQrToken('hello')).toBeNull();
    expect(extractQrToken('https://shop.example.com/item/42')).toBeNull();
    expect(extractQrToken('12345678901234')).toBeNull();
    expect(extractQrToken('has spaces in the middle of it')).toBeNull();
  });
});

describe('readTokenFromHash', () => {
  it('reads the token a ticket link carries after #', () => {
    expect(readTokenFromHash('#t=k3J9xQ2m_Lp8-ZtR4vW7yB1c')).toBe('k3J9xQ2m_Lp8-ZtR4vW7yB1c');
    expect(readTokenFromHash('#token=k3J9xQ2m_Lp8-ZtR4vW7yB1c')).toBe('k3J9xQ2m_Lp8-ZtR4vW7yB1c');
  });
  it('ignores an empty, foreign or malformed fragment', () => {
    expect(readTokenFromHash('')).toBeNull();
    expect(readTokenFromHash('#section-2')).toBeNull();
    expect(readTokenFromHash('#t=short')).toBeNull();
    expect(readTokenFromHash('#t=12345678901234')).toBeNull();
  });
});
