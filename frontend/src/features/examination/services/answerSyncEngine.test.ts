import { describe, expect, it, vi } from 'vitest';
import { AnswerSyncEngine, type PendingAnswer } from './answerSyncEngine';

const fatal = new Error('closed');

function setup(save: (a: PendingAnswer) => Promise<void>) {
  const timers: Array<() => void> = [];
  const onFatal = vi.fn();
  let clock = 1_000;
  const engine = new AnswerSyncEngine({
    save,
    isFatal: (e) => e === fatal,
    onFatal,
    now: () => clock++,
    setTimer: (fn) => {
      timers.push(fn);
      return timers.length;
    },
    clearTimer: () => undefined,
  });
  return { engine, timers, onFatal };
}

describe('AnswerSyncEngine', () => {
  it('saves queued answers and empties the queue', async () => {
    const save = vi.fn().mockResolvedValue(undefined);
    const { engine } = setup(save);
    engine.enqueue('q1', ['a']);
    expect(await engine.flush()).toBe(true);
    expect(save).toHaveBeenCalledWith(expect.objectContaining({ questionId: 'q1', optionIds: ['a'] }));
    expect(engine.getPending()).toHaveLength(0);
  });

  it('keeps the answer and schedules a retry after a network failure', async () => {
    const save = vi.fn().mockRejectedValueOnce(new Error('offline')).mockResolvedValue(undefined);
    const { engine, timers } = setup(save);
    engine.enqueue('q1', ['b']);
    expect(await engine.flush()).toBe(false);
    expect(engine.getPending()).toHaveLength(1);
    expect(engine.state.phase).toBe('retrying');

    timers.shift()!();
    expect(await engine.flush()).toBe(true);
    expect(engine.getPending()).toHaveLength(0);
  });

  it('never lets an older in-flight save erase a newer choice', async () => {
    let release!: () => void;
    const save = vi
      .fn()
      .mockImplementationOnce(() => new Promise<void>((r) => (release = r)))
      .mockResolvedValue(undefined);
    const { engine } = setup(save);

    engine.enqueue('q1', ['a']);
    engine.enqueue('q1', ['c']); // changes mind while the first save is in flight
    release();
    expect(await engine.flush()).toBe(true);

    const last = save.mock.calls.at(-1)![0] as PendingAnswer;
    expect(last.optionIds).toEqual(['c']);
    const first = save.mock.calls[0]![0] as PendingAnswer;
    expect(last.seq).toBeGreaterThan(first.seq);
  });

  it('stops and reports when the attempt is closed', async () => {
    const save = vi.fn().mockRejectedValue(fatal);
    const { engine, timers, onFatal } = setup(save);
    engine.enqueue('q1', ['a']);
    expect(await engine.flush()).toBe(false);
    expect(onFatal).toHaveBeenCalledTimes(1);
    expect(engine.state.phase).toBe('blocked');
    expect(timers).toHaveLength(0);
  });

  it('restores pending answers from a previous page load', async () => {
    const save = vi.fn().mockResolvedValue(undefined);
    const engine = new AnswerSyncEngine({ save, isFatal: () => false, initialPending: [{ questionId: 'q9', optionIds: ['d'], seq: 5 }] });
    expect(await engine.flush()).toBe(true);
    expect(save).toHaveBeenCalledWith({ questionId: 'q9', optionIds: ['d'], seq: 5 });
  });
});
