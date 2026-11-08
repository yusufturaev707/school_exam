/**
 * Memory Cards game logic — pure and UI-free, so it is unit-tested and the view stays thin.
 * The move log it records is what the backend replays to verify the result.
 */
export type CardStatus = 'hidden' | 'open' | 'matched';

export interface MemoryCard {
  id: string;
  face: string;
  status: CardStatus;
}

export interface MemoryState {
  cards: MemoryCard[];
  /** Ids of face-up, not-yet-matched cards (0–2). */
  open: string[];
  /** Every pair the player turned over, in order — sent to the backend on completion. */
  moves: Array<[string, string]>;
  matchedPairs: number;
  totalPairs: number;
  /** Last event, for announcements/animation. */
  last: 'none' | 'match' | 'miss';
}

export type MemoryAction = { type: 'flip'; id: string } | { type: 'hideMismatch' };

export function initMemory(cards: Array<{ id: string; face: string }>): MemoryState {
  return { cards: cards.map((c) => ({ ...c, status: 'hidden' })), open: [], moves: [], matchedPairs: 0, totalPairs: cards.length / 2, last: 'none' };
}

const setStatus = (cards: MemoryCard[], ids: string[], status: CardStatus) => cards.map((c) => (ids.includes(c.id) ? { ...c, status } : c));

export function memoryReducer(state: MemoryState, action: MemoryAction): MemoryState {
  if (action.type === 'hideMismatch') {
    if (state.open.length !== 2) return state;
    return { ...state, cards: setStatus(state.cards, state.open, 'hidden'), open: [], last: 'none' };
  }

  const card = state.cards.find((c) => c.id === action.id);
  if (!card || card.status !== 'hidden') return state;

  // A third tap while a mismatch is still showing: close the pair right away instead of blocking.
  let s = state.open.length === 2 ? memoryReducer(state, { type: 'hideMismatch' }) : state;

  const open = [...s.open, card.id];
  let cards = setStatus(s.cards, [card.id], 'open');
  if (open.length < 2) return { ...s, cards, open, last: 'none' };

  const [a, b] = open as [string, string];
  const moves: Array<[string, string]> = [...s.moves, [a, b]];
  const isMatch = cards.find((c) => c.id === a)!.face === cards.find((c) => c.id === b)!.face;
  if (isMatch) {
    cards = setStatus(cards, [a, b], 'matched');
    s = { ...s, cards, open: [], moves, matchedPairs: s.matchedPairs + 1, last: 'match' };
    return s;
  }
  return { ...s, cards, open, moves, last: 'miss' };
}

export const isMemoryComplete = (s: MemoryState) => s.matchedPairs === s.totalPairs;
