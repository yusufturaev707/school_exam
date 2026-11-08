import { describe, expect, it } from 'vitest';
import { initMemory, isMemoryComplete, memoryReducer, type MemoryAction, type MemoryState } from './memoryEngine';

const board = [
  { id: 'c1', face: 'cat' },
  { id: 'c2', face: 'sun' },
  { id: 'c3', face: 'cat' },
  { id: 'c4', face: 'sun' },
];
const run = (actions: MemoryAction[], s: MemoryState = initMemory(board)) => actions.reduce(memoryReducer, s);
const flip = (id: string): MemoryAction => ({ type: 'flip', id });

describe('memory engine', () => {
  it('keeps matching cards open and counts the move', () => {
    const s = run([flip('c1'), flip('c3')]);
    expect(s.matchedPairs).toBe(1);
    expect(s.cards.filter((c) => c.status === 'matched').map((c) => c.id)).toEqual(['c1', 'c3']);
    expect(s.moves).toEqual([['c1', 'c3']]);
    expect(s.last).toBe('match');
  });

  it('shows a mismatch until hidden, then closes both cards', () => {
    let s = run([flip('c1'), flip('c2')]);
    expect(s.last).toBe('miss');
    expect(s.open).toEqual(['c1', 'c2']);
    s = memoryReducer(s, { type: 'hideMismatch' });
    expect(s.cards.every((c) => c.status === 'hidden')).toBe(true);
    expect(s.moves).toHaveLength(1);
  });

  it('a third tap during a mismatch closes the pair and opens the new card', () => {
    const s = run([flip('c1'), flip('c2'), flip('c3')]);
    expect(s.open).toEqual(['c3']);
    expect(s.cards.find((c) => c.id === 'c1')!.status).toBe('hidden');
  });

  it('ignores taps on open/matched cards and the same card twice', () => {
    const s = run([flip('c1'), flip('c1'), flip('c3'), flip('c1'), flip('nope')]);
    expect(s.moves).toEqual([['c1', 'c3']]);
  });

  it('completes when every pair is found; move log replays on the server', () => {
    const s = run([flip('c1'), flip('c2'), flip('c3'), flip('c1'), flip('c2'), flip('c4')]);
    expect(isMemoryComplete(s)).toBe(true);
    expect(s.moves).toEqual([
      ['c1', 'c2'],
      ['c3', 'c1'],
      ['c2', 'c4'],
    ]);
  });
});
