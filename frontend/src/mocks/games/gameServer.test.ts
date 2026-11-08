import { describe, expect, it } from 'vitest';
import { createGamesState, GameApiError, handleGames, type GamesState } from './gameServer';
import { generateMemory, generateMissingNumber, generatePattern, replayMemory } from './generators';

const DIFFS = ['easy', 'medium', 'hard'] as const;
const key = (s: { type: string; color: string; rotation: number; count: number }) => `${s.type}|${s.color}|${s.rotation}|${s.count}`;

describe('generators', () => {
  it('missing number: one hidden term, 4 distinct options, exactly one correct, explanation shows the answer', () => {
    for (const d of DIFFS) {
      for (let run = 0; run < 150; run++) {
        const { questions } = generateMissingNumber(Math.random, d);
        expect(questions).toHaveLength(8);
        for (const q of questions) {
          expect(q.sequence.filter((v) => v === null)).toHaveLength(1);
          expect(q.sequence[0]).not.toBeNull();
          const values = q.options.map((o) => o.value);
          expect(new Set(values).size).toBe(4);
          expect(values.every((v) => v >= 0)).toBe(true);
          const answer = q.options.find((o) => o.id === q.correctOptionId)!.value;
          expect(q.explanation).toContain(`= ${answer}`);
        }
      }
    }
  });

  it('pattern: 6 visible shapes + hidden next, 4 distinct options with exactly one answer', () => {
    for (const d of DIFFS) {
      for (let run = 0; run < 150; run++) {
        const { questions } = generatePattern(Math.random, d);
        expect(questions).toHaveLength(6);
        for (const q of questions) {
          expect(q.sequence).toHaveLength(7);
          expect(q.sequence.slice(0, 6).every(Boolean)).toBe(true);
          expect(q.sequence[6]).toBeNull();
          expect(new Set(q.options.map((o) => key(o.shape))).size).toBe(4);
          expect(q.options.filter((o) => o.id === q.correctOptionId)).toHaveLength(1);
        }
      }
    }
  });

  it('memory: board has every face exactly twice; replay accepts real solutions and rejects forged ones', () => {
    const board = generateMemory(Math.random, 'hard');
    expect(board.cards).toHaveLength(16);
    const byFace = new Map<string, string[]>();
    for (const c of board.cards) byFace.set(c.face, [...(byFace.get(c.face) ?? []), c.id]);
    expect([...byFace.values()].every((ids) => ids.length === 2)).toBe(true);
    const solution = [...byFace.values()];
    expect(replayMemory(board.cards, solution)).toEqual({ valid: true, moves: 8, matchedPairs: 8 });
    expect(replayMemory(board.cards, solution.slice(1)).valid).toBe(false); // unfinished
    expect(replayMemory(board.cards, [...solution, solution[0]]).valid).toBe(false); // re-opening matched cards
    expect(replayMemory(board.cards, [['c1', 'c1']]).valid).toBe(false);
    expect(replayMemory(board.cards, 'all done').valid).toBe(false);
  });
});

describe('game server', () => {
  const NOW = Date.parse('2026-11-05T09:00:00Z');
  const call = (state: GamesState, method: string, path: string, body: Record<string, unknown> = {}, studentId = 'stu_a') =>
    handleGames(state, { method, path, body, studentId, now: NOW })!;

  it('never sends correct answers with the content', () => {
    const state = createGamesState();
    for (const slug of ['yashiringan-son', 'naqsh-ustasi']) {
      const { data } = call(state, 'POST', `/games/${slug}/start`, { difficulty: 'medium' });
      expect(JSON.stringify(data)).not.toMatch(/correctOptionId|explanation/);
    }
  });

  it('scores answers on the server, counts only the first answer, never goes negative, completes once', () => {
    const state = createGamesState();
    const { data } = call(state, 'POST', '/games/yashiringan-son/start', { difficulty: 'easy' }) as { data: { session: { id: string }; content: { questions: Array<{ id: string; options: Array<{ id: string }> }> } } };
    const sid = data.session.id;
    const rec = state.sessions[0]!;
    const q1 = rec.content.kind === 'missing-number' ? rec.content.questions[0]! : null;
    const wrong = q1!.options.find((o) => o.id !== q1!.correctOptionId)!.id;
    const r1 = call(state, 'POST', `/games/sessions/${sid}/answer`, { questionId: q1!.id, optionId: wrong }).data as { correct: boolean; score: number };
    expect(r1).toMatchObject({ correct: false, score: 0 });
    const r2 = call(state, 'POST', `/games/sessions/${sid}/answer`, { questionId: q1!.id, optionId: q1!.correctOptionId }).data as { correct: boolean; score: number };
    expect(r2).toMatchObject({ correct: false, score: 0 }); // retry can't flip the first answer

    const first = call(state, 'POST', `/games/sessions/${sid}/complete`).data as { score: number; newAchievements: Array<{ id: string }>; completedAt: string };
    const again = call(state, 'POST', `/games/sessions/${sid}/complete`).data as { score: number; newAchievements: Array<{ id: string }>; completedAt: string };
    expect(again).toEqual(first);
    expect(first.newAchievements.map((a) => a.id)).toContain('first-step');
    expect(() => call(state, 'POST', `/games/sessions/${sid}/answer`, { questionId: rec.content.kind === 'missing-number' ? rec.content.questions[1]!.id : '', optionId: 'x' })).toThrow(GameApiError);
  });

  it('memory: rejects a forged completion, accepts a real move log', () => {
    const state = createGamesState();
    const { data } = call(state, 'POST', '/games/xotira-kartalari/start', { difficulty: 'easy' }) as { data: { session: { id: string }; content: { cards: Array<{ id: string; face: string }> } } };
    expect(() => call(state, 'POST', `/games/sessions/${data.session.id}/complete`, { moves: [] })).toThrow(expect.objectContaining({ status: 422, code: 'INVALID_MOVES' }));
    const byFace = new Map<string, string[]>();
    for (const c of data.content.cards) byFace.set(c.face, [...(byFace.get(c.face) ?? []), c.id]);
    const res = call(state, 'POST', `/games/sessions/${data.session.id}/complete`, { moves: [...byFace.values()] }).data as { score: number; moves: number };
    expect(res).toMatchObject({ score: 40, moves: 4 });
  });

  it('hides other students’ sessions', () => {
    const state = createGamesState();
    const { data } = call(state, 'POST', '/games/naqsh-ustasi/start', { difficulty: 'easy' }) as { data: { session: { id: string } } };
    expect(() => call(state, 'POST', `/games/sessions/${data.session.id}/complete`, {}, 'stu_b')).toThrow(expect.objectContaining({ status: 404, code: 'SESSION_NOT_FOUND' }));
  });

  it('daily challenge is rewarded once and only for today’s game', () => {
    const state = createGamesState();
    const daily = call(state, 'GET', '/games/daily-challenge').data as { game: { slug: string }; difficulty: string; completed: boolean };
    expect(daily.completed).toBe(false);
    const other = ['xotira-kartalari', 'yashiringan-son', 'naqsh-ustasi'].find((s) => s !== daily.game.slug)!;
    const notDaily = call(state, 'POST', `/games/${other}/start`, { difficulty: daily.difficulty, daily: true }).data as { session: { isDaily: boolean } };
    expect(notDaily.session.isDaily).toBe(false);

    const start = call(state, 'POST', `/games/${daily.game.slug}/start`, { difficulty: daily.difficulty, daily: true }).data as { session: { id: string; isDaily: boolean } };
    expect(start.session.isDaily).toBe(true);
    const rec = state.sessions.find((s) => s.id === start.session.id)!;
    const pairs = new Map<string, string[]>();
    if (rec.content.kind === 'memory') for (const c of rec.content.cards) pairs.set(c.face, [...(pairs.get(c.face) ?? []), c.id]);
    const body = rec.content.kind === 'memory' ? { moves: [...pairs.values()] } : {};
    call(state, 'POST', `/games/sessions/${start.session.id}/complete`, body);
    expect((call(state, 'GET', '/games/daily-challenge').data as { completed: boolean }).completed).toBe(true);
    const second = call(state, 'POST', `/games/${daily.game.slug}/start`, { difficulty: daily.difficulty, daily: true }).data as { session: { isDaily: boolean } };
    expect(second.session.isDaily).toBe(false);
  });

  /** Plays a whole session, answering every quiz question correctly (or a valid memory log). */
  const playAll = (state: GamesState, sid: string) => {
    const rec = state.sessions.find((s) => s.id === sid)!;
    if (rec.content.kind === 'memory') {
      const pairs = new Map<string, string[]>();
      for (const c of rec.content.cards) pairs.set(c.face, [...(pairs.get(c.face) ?? []), c.id]);
      return call(state, 'POST', `/games/sessions/${sid}/complete`, { moves: [...pairs.values()] }).data as { score: number; bonus: number };
    }
    for (const q of rec.content.questions) call(state, 'POST', `/games/sessions/${sid}/answer`, { questionId: q.id, optionId: q.correctOptionId });
    return call(state, 'POST', `/games/sessions/${sid}/complete`).data as { score: number; bonus: number };
  };
  const totalScore = (state: GamesState) => (call(state, 'GET', '/student/games/statistics').data as { totalScore: number }).totalScore;

  it('daily challenge adds the advertised bonus on top of the score, once, and counts it in the total', () => {
    const state = createGamesState();
    const daily = call(state, 'GET', '/games/daily-challenge').data as { game: { slug: string }; difficulty: string; bonus: number };
    expect(daily.bonus).toBeGreaterThan(0);
    const a = call(state, 'POST', `/games/${daily.game.slug}/start`, { difficulty: daily.difficulty, daily: true }).data as { session: { id: string } };
    const b = call(state, 'POST', `/games/${daily.game.slug}/start`, { difficulty: daily.difficulty, daily: true }).data as { session: { id: string } };
    const ra = playAll(state, a.session.id);
    const rb = playAll(state, b.session.id); // a second daily session started in parallel earns no second bonus
    expect(ra.bonus).toBe(daily.bonus);
    expect(rb.bonus).toBe(0);
    expect(totalScore(state)).toBe(ra.score + rb.score + daily.bonus);
    const repeat = call(state, 'POST', `/games/sessions/${a.session.id}/complete`).data as { bonus: number };
    expect(repeat.bonus).toBe(daily.bonus); // idempotent
    expect(totalScore(state)).toBe(ra.score + rb.score + daily.bonus);
  });

  it('question of the day: hides the answer, keeps only the first reply, rewards a correct one', () => {
    const state = createGamesState();
    const q = call(state, 'GET', '/games/daily-question').data as { question: { id: string; options: Array<{ id: string; label: string }> }; answer: unknown; points: number };
    expect(q.answer).toBeNull();
    expect(JSON.stringify(q)).not.toContain('correct');
    const before = totalScore(state);
    // Try every option: the first one sticks.
    const first = call(state, 'POST', '/games/daily-question/answer', { questionId: q.question.id, optionId: q.question.options[0]!.id }).data as {
      answer: { selectedOptionId: string; correct: boolean; correctOptionId: string; pointsEarned: number };
    };
    const again = call(state, 'POST', '/games/daily-question/answer', { questionId: q.question.id, optionId: q.question.options[1]!.id }).data as typeof first;
    expect(again.answer.selectedOptionId).toBe(q.question.options[0]!.id);
    expect((call(state, 'GET', '/games/daily-question').data as typeof first).answer).toEqual(first.answer); // survives a reload
    expect(first.answer.pointsEarned).toBe(first.answer.correct ? q.points : 0);
    expect(totalScore(state)).toBe(before + first.answer.pointsEarned);
    expect(() => call(state, 'POST', '/games/daily-question/answer', { optionId: 'nope' })).toThrow(expect.objectContaining({ status: 422 }));
  });

  it('an unfinished session can be resumed with its checked answers, and abandoned for good', () => {
    const state = createGamesState();
    const start = call(state, 'POST', '/games/yashiringan-son/start', { difficulty: 'hard' }).data as { session: { id: string } };
    const sid = start.session.id;
    const rec = state.sessions.find((s) => s.id === sid)!;
    if (rec.content.kind !== 'missing-number') throw new Error('unexpected kind');
    const q0 = rec.content.questions[0]!;
    call(state, 'POST', `/games/sessions/${sid}/answer`, { questionId: q0.id, optionId: q0.correctOptionId });

    const resumed = call(state, 'GET', `/games/sessions/${sid}`).data as { session: { difficulty: string; score: number }; answers: Array<{ questionId: string; correct: boolean }>; content: unknown };
    expect(resumed.session).toMatchObject({ difficulty: 'hard', score: 10 });
    expect(resumed.answers).toEqual([expect.objectContaining({ questionId: q0.id, correct: true })]);
    expect(JSON.stringify(resumed.content)).not.toContain('correctOptionId'); // still no answers for open questions

    call(state, 'POST', `/games/sessions/${sid}/abandon`);
    call(state, 'POST', `/games/sessions/${sid}/abandon`); // idempotent
    expect(() => call(state, 'GET', `/games/sessions/${sid}`)).toThrow(expect.objectContaining({ status: 409, code: 'SESSION_ABANDONED' }));
    expect(() => call(state, 'POST', `/games/sessions/${sid}/complete`)).toThrow(expect.objectContaining({ code: 'SESSION_ABANDONED' }));
    expect(totalScore(state)).toBe(0); // an abandoned session gives nothing
  });

  it('badges that need games which are not playable yet are marked coming soon', () => {
    const state = createGamesState();
    const list = (call(state, 'GET', '/student/achievements').data as { achievements: Array<{ id: string; comingSoon: boolean }> }).achievements;
    expect(list.find((a) => a.id === 'attention-champion')?.comingSoon).toBe(true);
    expect(list.find((a) => a.id === 'memory-master')?.comingSoon).toBe(false);
    expect(list.find((a) => a.id === 'first-step')?.comingSoon).toBe(false);
  });
});
