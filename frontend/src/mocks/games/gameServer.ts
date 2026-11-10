/**
 * DEV-ONLY reference implementation of the Brain Games backend contract (docs/api-contract.md §Games).
 *
 * Storage-agnostic and framework-free so BOTH mock backends share it:
 *  - the in-browser axios adapter (src/mocks/installMockBackend.ts) imports it directly;
 *  - the Postman/Node HTTP mock loads a CommonJS build of it (`npm run mock:data`).
 *
 * Rules a real backend must also follow (and this mock does):
 *  - the server generates content and keeps correct answers to itself until a question is answered;
 *  - scores are computed only on the server (quiz answers are checked one by one; memory games
 *    are verified by replaying the client's move log);
 *  - completion is idempotent — repeats return the stored result, never a second reward;
 *  - a student can only see their own sessions (others get 404).
 */
import type { Achievement, GameCategory, GameDifficulty, GameResult, GameSession } from '@/features/brain-games/types';
import { CATALOG, CATEGORIES, type CatalogGame } from './catalog';
import {
  generateMemory,
  generateMissingNumber,
  generatePattern,
  replayMemory,
  type MemoryInternal,
  type MissingNumberInternal,
  type PatternInternal,
  type Rng,
} from './generators';

type InternalContent = MemoryInternal | MissingNumberInternal | PatternInternal;

export interface GameSessionRecord {
  id: string;
  studentId: string;
  gameId: string;
  difficulty: GameDifficulty;
  isDaily: boolean;
  startedAt: number;
  completedAt: number | null;
  /** `abandoned` — the student left (exit / restart); it can no longer be answered or completed. */
  status: 'in_progress' | 'completed' | 'abandoned';
  content: InternalContent;
  answers: Record<string, { optionId: string; correct: boolean }>;
  moves: number | null;
  score: number;
  /** Daily-challenge bonus, granted once at completion. Kept apart from `score` so the result screen can show it. */
  bonus?: number;
  maxScore: number;
  correctAnswers: number;
  totalQuestions: number;
  newAchievementIds: string[];
}

export interface GamesState {
  sessions: GameSessionRecord[];
  /** studentId → { 'YYYY-MM-DD': completedAt } */
  daily: Record<string, Record<string, number>>;
  /** studentId → { 'YYYY-MM-DD': first answer to the question of the day } */
  dailyQuestion?: Record<string, Record<string, { questionId: string; optionId: string; correct: boolean; at: number }>>;
}

export interface GamesRequest {
  method: string;
  /** Path without the `/api` prefix, e.g. `/games/xotira-kartalari`. */
  path: string;
  body: Record<string, unknown>;
  studentId: string;
  now: number;
  rng?: Rng;
}

export interface GamesResponse {
  status: number;
  data: unknown;
}

export class GameApiError extends Error {
  readonly isGameApiError = true;
  constructor(
    readonly status: number,
    readonly code: string,
    message?: string,
  ) {
    super(message ?? code);
  }
}

export const createGamesState = (): GamesState => ({ sessions: [], daily: {}, dailyQuestion: {} });

const POINTS_PER_CORRECT = 10;
/** Extra stars for finishing today's challenge (once per day). */
export const DAILY_BONUS = 20;
/** Stars for a correct first answer to the question of the day. */
export const DAILY_QUESTION_POINTS = 5;
const iso = (t: number) => new Date(t).toISOString();
const rid = (rng: Rng) => `gs_${Array.from({ length: 12 }, () => Math.floor(rng() * 36).toString(36)).join('')}`;

/** Calendar day in Tashkent (UTC+5), so the daily challenge flips at local midnight. */
export const tashkentDate = (now: number) => new Date(now + 5 * 3600_000).toISOString().slice(0, 10);

/* ------------------------------------------------------------------ catalogue */

function completedCount(state: GamesState, studentId: string, gameId: string) {
  return state.sessions.filter((s) => s.studentId === studentId && s.gameId === gameId && s.status === 'completed').length;
}

function publicGame(state: GamesState, studentId: string, g: CatalogGame) {
  return { ...g, completedCount: completedCount(state, studentId, g.id) };
}

function findGame(idOrSlug: string): CatalogGame {
  const g = CATALOG.find((x) => x.id === idOrSlug || x.slug === idOrSlug);
  if (!g) throw new GameApiError(404, 'GAME_NOT_FOUND');
  return g;
}

/* ------------------------------------------------------------------ content */

function generate(g: CatalogGame, difficulty: GameDifficulty, rng: Rng): InternalContent {
  switch (g.kind) {
    case 'memory':
      return generateMemory(rng, difficulty);
    case 'missing-number':
      return generateMissingNumber(rng, difficulty);
    case 'pattern':
      return generatePattern(rng, difficulty);
    default:
      throw new GameApiError(409, 'GAME_NOT_AVAILABLE');
  }
}

/** What the client may see: no correct answers, no explanations. */
function publicContent(c: InternalContent) {
  if (c.kind === 'memory') return c;
  if (c.kind === 'missing-number') return { kind: c.kind, questions: c.questions.map(({ id, sequence, options }) => ({ id, sequence, options })) };
  return { kind: c.kind, questions: c.questions.map(({ id, sequence, options }) => ({ id, sequence, options })) };
}

const questionCount = (c: InternalContent) => (c.kind === 'memory' ? c.pairs : c.questions.length);

/* ------------------------------------------------------------------ achievements */

interface AchievementRule {
  id: string;
  title: string;
  description: string;
  icon: string;
  target: number;
  /** Set when the rule needs games of one category — if none is active yet, the badge is "coming soon". */
  category?: GameCategory;
  /** Progress after a list of completed sessions (chronological). */
  measure: (done: GameSessionRecord[], dailyCount: number) => number;
}

const categoryOf = (s: GameSessionRecord): GameCategory => findGame(s.gameId).category;
const countIn = (cat: GameCategory) => (done: GameSessionRecord[]) => done.filter((s) => categoryOf(s) === cat).length;

// Participation and exploration only — no streaks, no "play every day" pressure.
const ACHIEVEMENTS: AchievementRule[] = [
  { id: 'first-step', title: 'Birinchi qadam', description: 'Birinchi oʻyinni yakunlang.', icon: 'footprints', target: 1, measure: (d) => d.length },
  { id: 'memory-master', title: 'Xotira ustasi', description: 'Xotira oʻyinini yakunlang.', icon: 'brain', target: 1, category: 'memory', measure: countIn('memory') },
  { id: 'math-explorer', title: 'Matematik izquvar', description: '3 ta matematika oʻyinini yakunlang.', icon: 'calculator', target: 3, category: 'math', measure: countIn('math') },
  { id: 'logic-thinker', title: 'Mantiqiy fikrlovchi', description: '3 ta mantiq oʻyinini yakunlang.', icon: 'puzzle', target: 3, category: 'logic', measure: countIn('logic') },
  { id: 'attention-champion', title: 'Diqqat chempioni', description: 'Diqqat oʻyinini yakunlang.', icon: 'eye', target: 1, category: 'attention', measure: countIn('attention') },
  { id: 'curious-mind', title: 'Izlanuvchan bola', description: '3 xil yoʻnalishdagi oʻyinlarni sinab koʻring.', icon: 'compass', target: 3, measure: (d) => new Set(d.map(categoryOf)).size },
  { id: 'daily-explorer', title: 'Kun kashfiyotchisi', description: 'Bugungi intellektual topshiriqni bajaring.', icon: 'sun', target: 1, measure: (_d, daily) => daily },
];

function achievementsFor(state: GamesState, studentId: string): Achievement[] {
  const done = state.sessions.filter((s) => s.studentId === studentId && s.status === 'completed').sort((a, b) => a.completedAt! - b.completedAt!);
  const dailyDays = Object.values(state.daily[studentId] ?? {}).sort((a, b) => a - b);
  return ACHIEVEMENTS.map((rule) => {
    // Unlock time = completion time of the session that first satisfied the rule.
    let unlockedAt: number | null = null;
    for (let i = 0; i < done.length && unlockedAt === null; i++) {
      const at = done[i]!.completedAt!;
      if (rule.measure(done.slice(0, i + 1), dailyDays.filter((d) => d <= at).length) >= rule.target) unlockedAt = at;
    }
    const current = Math.min(rule.target, rule.measure(done, dailyDays.length));
    // A badge that needs games nobody can play yet is shown as "coming soon", never as a task to fail at.
    const comingSoon = unlockedAt === null && rule.category !== undefined && !CATALOG.some((g) => g.category === rule.category && g.isActive);
    return {
      id: rule.id,
      title: rule.title,
      description: rule.description,
      icon: rule.icon,
      unlockedAt: unlockedAt === null ? null : iso(unlockedAt),
      progress: { current, target: rule.target },
      comingSoon,
    };
  });
}

/* ------------------------------------------------------------------ daily challenge */

const ACTIVE = () => CATALOG.filter((g) => g.isActive);

function dailyFor(state: GamesState, studentId: string, now: number) {
  const date = tashkentDate(now);
  const dayNumber = Math.floor(Date.parse(`${date}T00:00:00Z`) / 864e5);
  const active = ACTIVE();
  const game = active[dayNumber % active.length]!;
  const difficulty: GameDifficulty = (['easy', 'medium', 'medium', 'hard'] as const)[dayNumber % 4]!;
  const completedAt = state.daily[studentId]?.[date] ?? null;
  return { date, game, difficulty, completedAt };
}

/* ------------------------------------------------------------------ question of the day */

interface DailyQuestionItem {
  id: string;
  prompt: string;
  sequence: string;
  options: string[];
  correct: string;
  explanation: string;
}

// The server keeps the right answer; the client only learns it after its (single) answer.
const DAILY_QUESTIONS: DailyQuestionItem[] = [
  { id: 'dq-odd-powers', prompt: 'Qaysi son ortiqcha?', sequence: '3 · 9 · 12 · 27 · 81', options: ['3', '9', '12', '81'], correct: '12', explanation: 'Qolganlari 3 ning darajalari: 3, 9, 27, 81.' },
  { id: 'dq-doubling', prompt: 'Keyingi son qaysi?', sequence: '2 · 4 · 8 · 16 · ?', options: ['18', '24', '32', '20'], correct: '32', explanation: 'Har bir son oldingisidan 2 marta katta.' },
  { id: 'dq-odd-word', prompt: 'Qaysi soʻz ortiqcha?', sequence: 'olma · nok · sabzi · uzum', options: ['olma', 'nok', 'sabzi', 'uzum'], correct: 'sabzi', explanation: 'Sabzi — sabzavot, qolganlari meva.' },
  { id: 'dq-fibonacci', prompt: 'Keyingi son qaysi?', sequence: '1 · 1 · 2 · 3 · 5 · ?', options: ['6', '7', '8', '9'], correct: '8', explanation: 'Har bir son oldingi ikkitasining yigʻindisi.' },
  { id: 'dq-fives', prompt: 'Qaysi son ortiqcha?', sequence: '5 · 10 · 15 · 21 · 25', options: ['10', '15', '21', '25'], correct: '21', explanation: 'Qolganlari 5 ga boʻlinadi.' },
  { id: 'dq-minus-three', prompt: 'Yetishmayotgan son?', sequence: '10 · 7 · ? · 1', options: ['3', '4', '5', '6'], correct: '4', explanation: 'Har qadamda 3 kamayadi.' },
  { id: 'dq-not-shape', prompt: 'Qaysi soʻz ortiqcha?', sequence: 'doira · kvadrat · uchburchak · qalam', options: ['doira', 'kvadrat', 'uchburchak', 'qalam'], correct: 'qalam', explanation: 'Qalam — shakl emas.' },
];

const optionId = (q: DailyQuestionItem, i: number) => `${q.id}-o${i + 1}`;

function dailyQuestionFor(state: GamesState, studentId: string, now: number) {
  const date = tashkentDate(now);
  const dayNumber = Math.floor(Date.parse(`${date}T00:00:00Z`) / 864e5);
  const q = DAILY_QUESTIONS[dayNumber % DAILY_QUESTIONS.length]!;
  const record = state.dailyQuestion?.[studentId]?.[date];
  const correctOptionId = optionId(q, q.options.indexOf(q.correct));
  return {
    date,
    q,
    dto: {
      date,
      question: { id: q.id, prompt: q.prompt, sequence: q.sequence, options: q.options.map((label, i) => ({ id: optionId(q, i), label })) },
      points: DAILY_QUESTION_POINTS,
      answer: record
        ? { selectedOptionId: record.optionId, correct: record.correct, correctOptionId, explanation: q.explanation, pointsEarned: record.correct ? DAILY_QUESTION_POINTS : 0, answeredAt: iso(record.at) }
        : null,
    },
  };
}

const dailyQuestionPoints = (state: GamesState, studentId: string) =>
  Object.values(state.dailyQuestion?.[studentId] ?? {}).filter((r) => r.correct).length * DAILY_QUESTION_POINTS;

/* ------------------------------------------------------------------ projections */

function sessionDto(s: GameSessionRecord): GameSession {
  return {
    id: s.id,
    gameId: s.gameId,
    gameSlug: findGame(s.gameId).slug,
    difficulty: s.difficulty,
    isDaily: s.isDaily,
    startedAt: iso(s.startedAt),
    completedAt: s.completedAt === null ? null : iso(s.completedAt),
    status: s.status,
    score: s.score,
    correctAnswers: s.correctAnswers,
    totalQuestions: s.totalQuestions,
  };
}

/** Everything needed to continue an unfinished session after a page reload. */
function resumeDto(s: GameSessionRecord) {
  const questions = s.content.kind === 'memory' ? [] : (s.content.questions as Array<{ id: string; correctOptionId: string; explanation: string }>);
  return {
    session: sessionDto(s),
    content: publicContent(s.content),
    answers: questions
      .filter((q) => s.answers[q.id])
      .map((q) => ({ questionId: q.id, optionId: s.answers[q.id]!.optionId, correct: s.answers[q.id]!.correct, correctOptionId: q.correctOptionId, explanation: q.explanation })),
  };
}

function resultDto(state: GamesState, s: GameSessionRecord): GameResult {
  const g = findGame(s.gameId);
  const all = achievementsFor(state, s.studentId);
  return {
    sessionId: s.id,
    game: { id: g.id, slug: g.slug, title: g.title, category: g.category },
    difficulty: s.difficulty,
    score: s.score,
    bonus: s.bonus ?? 0,
    maxScore: s.maxScore,
    correctAnswers: s.correctAnswers,
    totalQuestions: s.totalQuestions,
    durationSeconds: Math.max(0, Math.round((s.completedAt! - s.startedAt) / 1000)),
    moves: s.moves,
    completedAt: iso(s.completedAt!),
    isDaily: s.isDaily,
    newAchievements: all.filter((a) => s.newAchievementIds.includes(a.id)),
  };
}

/* ------------------------------------------------------------------ mutations */

function complete(state: GamesState, s: GameSessionRecord, body: Record<string, unknown>, now: number) {
  if (s.status === 'completed') return; // idempotent: never re-score or re-reward
  if (s.status === 'abandoned') throw new GameApiError(409, 'SESSION_ABANDONED');
  if (s.content.kind === 'memory') {
    const replay = replayMemory(s.content.cards, body.moves);
    if (!replay.valid) throw new GameApiError(422, 'INVALID_MOVES', 'Move log does not solve this board');
    s.moves = replay.moves;
    s.correctAnswers = replay.matchedPairs;
    s.score = replay.matchedPairs * POINTS_PER_CORRECT; // finishing is what counts — no time or move penalties
  }
  const before = new Set(achievementsFor(state, s.studentId).filter((a) => a.unlockedAt).map((a) => a.id));
  s.status = 'completed';
  s.completedAt = now;
  if (s.isDaily) {
    const date = tashkentDate(s.startedAt);
    const days = (state.daily[s.studentId] ??= {});
    // Bonus only for the session that actually earns today's challenge (two parallel daily sessions ≠ two bonuses).
    if (days[date] === undefined) s.bonus = DAILY_BONUS;
    days[date] ??= now;
  }
  s.newAchievementIds = achievementsFor(state, s.studentId)
    .filter((a) => a.unlockedAt && !before.has(a.id))
    .map((a) => a.id);
}

/* ------------------------------------------------------------------ router */

export function handleGames(state: GamesState, req: GamesRequest): GamesResponse | null {
  const { method, path, body, studentId, now } = req;
  const rng = req.rng ?? Math.random;
  const ok = (data: unknown, status = 200): GamesResponse => ({ status, data });
  let m: RegExpMatchArray | null;

  const own = (id: string) => {
    const s = state.sessions.find((x) => x.id === id);
    if (!s || s.studentId !== studentId) throw new GameApiError(404, 'SESSION_NOT_FOUND'); // never reveal others' sessions
    return s;
  };

  if (method === 'GET' && path === '/games') return ok({ games: CATALOG.map((g) => publicGame(state, studentId, g)) });

  if (method === 'GET' && path === '/games/categories') {
    return ok({
      categories: CATEGORIES.map((c) => ({
        ...c,
        gameCount: CATALOG.filter((g) => g.category === c.id).length,
        activeCount: CATALOG.filter((g) => g.category === c.id && g.isActive).length,
      })),
    });
  }

  if (method === 'GET' && path === '/games/daily-challenge') {
    const d = dailyFor(state, studentId, now);
    return ok({ date: d.date, game: publicGame(state, studentId, d.game), difficulty: d.difficulty, completed: d.completedAt !== null, completedAt: d.completedAt === null ? null : iso(d.completedAt), bonus: DAILY_BONUS });
  }

  if (method === 'GET' && path === '/games/daily-question') return ok(dailyQuestionFor(state, studentId, now).dto);

  if (method === 'POST' && path === '/games/daily-question/answer') {
    const { date, q } = dailyQuestionFor(state, studentId, now);
    const chosen = String(body.optionId ?? '');
    const index = q.options.findIndex((_, i) => optionId(q, i) === chosen);
    if (index < 0 || (body.questionId !== undefined && body.questionId !== q.id)) throw new GameApiError(422, 'INVALID_ANSWER');
    const mine = ((state.dailyQuestion ??= {})[studentId] ??= {});
    // Only the first answer of the day counts; repeats (refresh, double tap) return the stored one.
    mine[date] ??= { questionId: q.id, optionId: chosen, correct: q.options[index] === q.correct, at: now };
    return ok(dailyQuestionFor(state, studentId, now).dto);
  }

  if (method === 'GET' && (m = path.match(/^\/games\/sessions\/([^/]+)$/))) {
    const s = own(m[1]!);
    if (s.status !== 'in_progress') throw new GameApiError(409, s.status === 'completed' ? 'SESSION_COMPLETED' : 'SESSION_ABANDONED');
    return ok(resumeDto(s));
  }

  if (method === 'POST' && (m = path.match(/^\/games\/sessions\/([^/]+)\/abandon$/))) {
    const s = own(m[1]!);
    if (s.status === 'in_progress') s.status = 'abandoned'; // idempotent; a completed session stays completed
    return ok({ session: sessionDto(s) });
  }

  // Explicit completion endpoint from the contract; finishing a daily session already records it.
  if (method === 'POST' && path === '/games/daily-challenge/complete') {
    const s = own(String(body.sessionId ?? ''));
    if (!s.isDaily || s.status !== 'completed') throw new GameApiError(409, 'NOT_A_COMPLETED_DAILY_SESSION');
    const date = tashkentDate(s.startedAt);
    const days = (state.daily[studentId] ??= {});
    days[date] ??= s.completedAt!;
    return ok({ date, completed: true, completedAt: iso(days[date]!) });
  }

  if (method === 'GET' && (m = path.match(/^\/games\/sessions\/([^/]+)\/result$/))) {
    const s = own(m[1]!);
    if (s.status !== 'completed') throw new GameApiError(409, 'SESSION_NOT_COMPLETED');
    return ok(resultDto(state, s));
  }

  if (method === 'POST' && (m = path.match(/^\/games\/sessions\/([^/]+)\/answer$/))) {
    const s = own(m[1]!);
    if (s.content.kind === 'memory') throw new GameApiError(400, 'ANSWERS_NOT_SUPPORTED');
    const qid = String(body.questionId ?? '');
    const question = (s.content.questions as Array<{ id: string; options: Array<{ id: string }>; correctOptionId: string; explanation: string }>).find((q) => q.id === qid);
    const optionId = String(body.optionId ?? '');
    if (!question || !question.options.some((o) => o.id === optionId)) throw new GameApiError(422, 'INVALID_ANSWER');
    const existing = s.answers[qid];
    if (!existing) {
      if (s.status !== 'in_progress') throw new GameApiError(409, s.status === 'completed' ? 'SESSION_COMPLETED' : 'SESSION_ABANDONED');
      const correct = optionId === question.correctOptionId;
      s.answers[qid] = { optionId, correct }; // first answer counts; retries are idempotent
      if (correct) {
        s.correctAnswers++;
        s.score += POINTS_PER_CORRECT; // wrong answers give 0 — never negative
      }
    }
    return ok({ questionId: qid, correct: s.answers[qid]!.correct, correctOptionId: question.correctOptionId, explanation: question.explanation, score: s.score, correctAnswers: s.correctAnswers });
  }

  if (method === 'POST' && (m = path.match(/^\/games\/sessions\/([^/]+)\/complete$/))) {
    const s = own(m[1]!);
    complete(state, s, body, now);
    return ok(resultDto(state, s));
  }

  if (method === 'POST' && (m = path.match(/^\/games\/([^/]+)\/start$/))) {
    const g = findGame(m[1]!);
    if (!g.isActive) throw new GameApiError(409, 'GAME_NOT_AVAILABLE');
    const difficulty = String(body.difficulty ?? g.difficulties[0]) as GameDifficulty;
    if (!g.difficulties.includes(difficulty)) throw new GameApiError(422, 'INVALID_DIFFICULTY');
    // Daily reward only for today's game/difficulty and only until it's earned once.
    const daily = dailyFor(state, studentId, now);
    const isDaily = body.daily === true && daily.game.id === g.id && daily.difficulty === difficulty && daily.completedAt === null;
    const content = generate(g, difficulty, rng);
    const total = questionCount(content);
    const s: GameSessionRecord = {
      id: rid(rng),
      studentId,
      gameId: g.id,
      difficulty,
      isDaily,
      startedAt: now,
      completedAt: null,
      status: 'in_progress',
      content,
      answers: {},
      moves: null,
      score: 0,
      maxScore: total * POINTS_PER_CORRECT,
      correctAnswers: 0,
      totalQuestions: total,
      newAchievementIds: [],
    };
    state.sessions.push(s);
    // Keep the store small: drop abandoned sessions older than a day.
    state.sessions = state.sessions.filter((x) => x.status === 'completed' || now - x.startedAt < 864e5);
    return ok({ session: sessionDto(s), content: publicContent(content) }, 201);
  }

  if (method === 'GET' && (m = path.match(/^\/games\/([^/]+)$/))) return ok({ game: publicGame(state, studentId, findGame(m[1]!)) });

  if (method === 'GET' && path === '/student/achievements') return ok({ achievements: achievementsFor(state, studentId) });

  if (method === 'GET' && path === '/student/games/statistics') {
    const done = state.sessions.filter((s) => s.studentId === studentId && s.status === 'completed').sort((a, b) => b.completedAt! - a.completedAt!);
    return ok({
      totalCompleted: done.length,
      // Every star the student earned: game points + daily bonuses + question-of-the-day points.
      totalScore: done.reduce((a, s) => a + s.score + (s.bonus ?? 0), 0) + dailyQuestionPoints(state, studentId),
      categories: CATEGORIES.map((c) => ({ category: c.id, completed: done.filter((s) => categoryOf(s) === c.id).length })),
      games: ACTIVE().map((g) => {
        const mine = done.filter((s) => s.gameId === g.id);
        const best = mine.reduce<GameSessionRecord | null>((b, s) => (!b || s.score / (s.maxScore || 1) > b.score / (b.maxScore || 1) ? s : b), null);
        return { gameId: g.id, slug: g.slug, title: g.title, category: g.category, completed: mine.length, bestScore: best?.score ?? null, maxScore: best?.maxScore ?? null };
      }),
      recent: done.slice(0, 10).map((s) => {
        const g = findGame(s.gameId);
        return { sessionId: s.id, slug: g.slug, title: g.title, category: g.category, score: s.score, bonus: s.bonus ?? 0, maxScore: s.maxScore, completedAt: iso(s.completedAt!) };
      }),
    });
  }

  return null; // not a games route
}

/** Seeds a little history for a demo student so statistics/achievements have something to show. */
export function seedGameHistory(state: GamesState, studentId: string, now: number, rng: Rng = Math.random) {
  const play = (slug: string, difficulty: GameDifficulty, agoMs: number, correctRatio: number) => {
    const start = handleGames(state, { method: 'POST', path: `/games/${slug}/start`, body: { difficulty }, studentId, now: now - agoMs, rng })!;
    const { session } = start.data as { session: { id: string } };
    const rec = state.sessions.find((s) => s.id === session.id)!;
    if (rec.content.kind === 'memory') {
      const byFace = new Map<string, string[]>();
      for (const c of rec.content.cards) byFace.set(c.face, [...(byFace.get(c.face) ?? []), c.id]);
      const pairs = [...byFace.values()];
      // One miss first (two different faces), then every pair — a realistic, valid move log.
      const moves = [[pairs[0]![0]!, pairs[1]![0]!], ...pairs];
      handleGames(state, { method: 'POST', path: `/games/sessions/${session.id}/complete`, body: { moves }, studentId, now: now - agoMs + 95_000, rng });
      return;
    }
    const questions: Array<{ id: string; correctOptionId: string; options: Array<{ id: string }> }> = rec.content.questions;
    questions.forEach((q, i) => {
      const optionId = i / questions.length < correctRatio ? q.correctOptionId : q.options.find((o) => o.id !== q.correctOptionId)!.id;
      handleGames(state, { method: 'POST', path: `/games/sessions/${session.id}/answer`, body: { questionId: q.id, optionId }, studentId, now: now - agoMs + 10_000 * (i + 1), rng });
    });
    handleGames(state, { method: 'POST', path: `/games/sessions/${session.id}/complete`, body: {}, studentId, now: now - agoMs + 150_000, rng });
  };
  play('xotira-kartalari', 'easy', 2 * 864e5, 1);
  play('yashiringan-son', 'easy', 864e5, 0.75);
}
