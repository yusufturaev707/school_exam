import { useSyncExternalStore } from 'react';

/** Yorugʻ / qorongʻi rejim. `system` — qurilma sozlamasiga ergashadi. index.html dagi skript bilan bir xil kalit. */
export type ThemePref = 'light' | 'dark' | 'system';

/** All app keys are namespaced `bilimdon:*`; the app never reads keys it does not own. */
const KEY = 'bilimdon:theme';
const LEGACY_KEY = 'bilimdon-theme';
const media = typeof window !== 'undefined' ? window.matchMedia('(prefers-color-scheme: dark)') : null;
const listeners = new Set<() => void>();

function readPref(): ThemePref {
  try {
    const legacy = localStorage.getItem(LEGACY_KEY); // one-time move from the old key name
    if (legacy !== null) {
      localStorage.setItem(KEY, legacy);
      localStorage.removeItem(LEGACY_KEY);
    }
    const v = localStorage.getItem(KEY);
    return v === 'light' || v === 'dark' ? v : 'system';
  } catch {
    return 'system';
  }
}

function apply(pref: ThemePref) {
  const dark = pref === 'dark' || (pref === 'system' && !!media?.matches);
  document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', dark ? '#0e1714' : '#f4f7f2');
}

let current: ThemePref = typeof window !== 'undefined' ? readPref() : 'system';
if (typeof window !== 'undefined') {
  apply(current);
  media?.addEventListener('change', () => {
    if (current === 'system') {
      apply(current);
      listeners.forEach((l) => l());
    }
  });
}

export function setTheme(pref: ThemePref) {
  current = pref;
  try {
    if (pref === 'system') localStorage.removeItem(KEY);
    else localStorage.setItem(KEY, pref);
  } catch {
    /* private mode — rejim faqat shu sessiyada ishlaydi */
  }
  apply(pref);
  listeners.forEach((l) => l());
}

export const isDarkNow = () => document.documentElement.getAttribute('data-theme') === 'dark';

export function useTheme() {
  const pref = useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => current,
  );
  const dark = useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    isDarkNow,
  );
  return { pref, dark, setTheme };
}
