import type { GameDifficulty } from '../types';

/*
 * Survives a page reload (sessionStorage — per tab, cleared when the tab closes or on logout):
 *  - the unfinished game session, so the student can choose “Davom ettirish” or “Qaytadan boshlash”;
 *  - the last level picked for each game.
 * No identity data. Progress itself (answers, score) is always re-read from the server.
 */
export interface ActiveGame {
  sessionId: string;
  slug: string;
  difficulty: GameDifficulty;
  daily: boolean;
  startedAt: number;
}

const ACTIVE = 'bilimdon:game:active';
const level = (slug: string) => `bilimdon:game:level:${slug}`;

function read<T>(key: string): T | null {
  try {
    const raw = sessionStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

function write(key: string, value: unknown) {
  try {
    if (value === null) sessionStorage.removeItem(key);
    else sessionStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* storage unavailable — the game still works, it just can't be resumed after a reload */
  }
}

export function loadActiveGame(slug?: string): ActiveGame | null {
  const a = read<ActiveGame>(ACTIVE);
  if (!a || typeof a.sessionId !== 'string' || typeof a.slug !== 'string') return null;
  if (Date.now() - (a.startedAt ?? 0) > 6 * 3600_000) return null; // stale (server drops abandoned sessions after a day)
  return slug && a.slug !== slug ? null : a;
}

export const saveActiveGame = (a: ActiveGame) => write(ACTIVE, a);
export const clearActiveGame = () => write(ACTIVE, null);

export const loadLevel = (slug: string) => read<GameDifficulty>(level(slug)) ?? undefined;
export const saveLevel = (slug: string, d: GameDifficulty) => write(level(slug), d);

export function clearGameSessionStorage() {
  try {
    Object.keys(sessionStorage)
      .filter((k) => k.startsWith('bilimdon:game:'))
      .forEach((k) => sessionStorage.removeItem(k));
  } catch {
    /* ignore */
  }
}
