import type { PendingAnswer } from './answerSyncEngine';

/**
 * Per-tab persistence of exam UI state that must survive a refresh:
 *  - answers not yet confirmed by the server (so a refresh mid-save never loses a choice),
 *  - the submit idempotency key (so a retried submit after refresh is still deduplicated),
 *  - the question the student was looking at.
 * sessionStorage only: no identity data, cleared when the tab closes or on logout.
 */
export interface PersistedAttemptState {
  pending: PendingAnswer[];
  submitKey: string | null;
  currentIndex: number;
}

const PREFIX = 'bilimdon:exam:';
const LEGACY_PREFIX = 'bilimdon.exam.';
const key = (attemptId: string) => `${PREFIX}${attemptId}`;

export function loadAttemptState(attemptId: string): PersistedAttemptState {
  const empty: PersistedAttemptState = { pending: [], submitKey: null, currentIndex: 0 };
  try {
    // An attempt saved under the old key name (before an update, mid-exam) is still picked up.
    const raw = sessionStorage.getItem(key(attemptId)) ?? sessionStorage.getItem(`${LEGACY_PREFIX}${attemptId}`);
    if (!raw) return empty;
    const parsed = JSON.parse(raw) as Partial<PersistedAttemptState>;
    return {
      pending: Array.isArray(parsed.pending)
        ? parsed.pending.filter((p): p is PendingAnswer => typeof p?.questionId === 'string' && Array.isArray(p.optionIds) && typeof p.seq === 'number')
        : [],
      submitKey: typeof parsed.submitKey === 'string' ? parsed.submitKey : null,
      currentIndex: typeof parsed.currentIndex === 'number' ? parsed.currentIndex : 0,
    };
  } catch {
    return empty;
  }
}

export function saveAttemptState(attemptId: string, patch: Partial<PersistedAttemptState>): void {
  try {
    const next = { ...loadAttemptState(attemptId), ...patch };
    sessionStorage.setItem(key(attemptId), JSON.stringify(next));
  } catch {
    /* storage unavailable (private mode / quota) — the in-memory queue still works */
  }
}

export function clearAttemptState(attemptId: string): void {
  try {
    sessionStorage.removeItem(key(attemptId));
    sessionStorage.removeItem(`${LEGACY_PREFIX}${attemptId}`);
  } catch {
    /* ignore */
  }
}

export function clearExamSessionStorage(): void {
  try {
    Object.keys(sessionStorage)
      .filter((k) => k.startsWith(PREFIX) || k.startsWith(LEGACY_PREFIX))
      .forEach((k) => sessionStorage.removeItem(k));
  } catch {
    /* ignore */
  }
}

export function newIdempotencyKey(): string {
  return crypto.randomUUID?.() ?? `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}-${Math.random().toString(36).slice(2)}`;
}
