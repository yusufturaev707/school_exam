/**
 * DEV-ONLY in-browser mock backend, installed as an axios adapter when VITE_USE_MOCKS=true.
 *
 * It simulates the proposed API contract (docs/api-contract.md) closely enough to exercise every
 * frontend state: server-side deadlines, idempotent submit, clientSeq ordering, QR token errors,
 * offline behaviour (DevTools → Network → Offline) and session expiry. It is NOT security:
 * real authentication, timing and scoring must be implemented by the backend.
 */
import { AxiosError, AxiosHeaders, type AxiosInstance, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios';
import { QUESTIONS, publicQuestions } from './questionBank';
import { createGamesState, GameApiError, handleGames, type GamesState } from './games/gameServer';
import type { Answers } from '@/features/examination/types';

type Json = Record<string, unknown>;

interface MockAttempt {
  id: string;
  examId: string;
  status: 'in_progress' | 'submitted' | 'expired';
  startedAt: number;
  expiresAt: number;
  answers: Record<string, { ids: string[]; seq: number }>;
  submitKeys: string[];
  resultId: string | null;
}
interface MockResult {
  id: string;
  attemptId: string;
  completedAt: number;
  finishReason: 'manual' | 'timeout';
}
interface MockDb {
  studentId: string | null;
  usedQr: string[];
  attempts: MockAttempt[];
  results: MockResult[];
  games: GamesState;
}

const STUDENT = { id: 'stu_8f2k1', firstName: 'Aziz', lastName: 'Karimov', className: '6-“B” sinf', schoolName: '12-maktab', photoUrl: null };
const DEMO_JSHSHIR = '12345678901234';
const EXAM = {
  id: 'exam-autumn-2026',
  title: 'Kuzgi bilimlar imtihoni',
  description: 'Matematika, mantiq va ona tili bo‘yicha 45 ta qiziqarli savol.',
  durationMinutes: 60,
  sections: [
    { subject: 'math', title: 'Matematika', questionCount: 15 },
    { subject: 'iq', title: 'Mantiq (IQ)', questionCount: 15 },
    { subject: 'language', title: 'Ona tili va adabiyot', questionCount: 15 },
  ],
};
const DURATION_MS = (Number(import.meta.env.VITE_MOCK_EXAM_SECONDS) || EXAM.durationMinutes * 60) * 1000;
const GRACE_MS = 15_000;
const KEY = 'bilimdon:mockdb';

const empty = (): MockDb => ({ studentId: null, usedQr: [], attempts: [], results: [], games: createGamesState() });
const load = (): MockDb => {
  try {
    return { ...empty(), ...(JSON.parse(sessionStorage.getItem(KEY) ?? '{}') as Partial<MockDb>) };
  } catch {
    return empty();
  }
};
const save = (db: MockDb) => sessionStorage.setItem(KEY, JSON.stringify(db));
const uid = (p: string) => `${p}_${Math.random().toString(36).slice(2, 10)}`;

class HttpError {
  constructor(
    readonly status: number,
    readonly code: string,
    readonly message = code,
  ) {}
}

function finalize(db: MockDb, attempt: MockAttempt, reason: 'manual' | 'timeout') {
  if (attempt.status !== 'in_progress') return;
  attempt.status = reason === 'timeout' ? 'expired' : 'submitted';
  const result: MockResult = { id: uid('res'), attemptId: attempt.id, completedAt: Math.min(Date.now(), attempt.expiresAt), finishReason: reason };
  db.results.unshift(result);
  attempt.resultId = result.id;
}

/** Mirrors the backend deadline policy: attempts past their deadline are finalised on any access. */
function sweep(db: MockDb) {
  for (const a of db.attempts) if (a.status === 'in_progress' && Date.now() > a.expiresAt + GRACE_MS) finalize(db, a, 'timeout');
}

function score(attempt: MockAttempt) {
  const bySubject = { math: { c: 0, i: 0, u: 0, t: 0 }, iq: { c: 0, i: 0, u: 0, t: 0 }, language: { c: 0, i: 0, u: 0, t: 0 } };
  for (const q of QUESTIONS) {
    const s = bySubject[q.subject];
    s.t++;
    const ids = attempt.answers[q.id]?.ids ?? [];
    if (ids.length === 0) s.u++;
    else if (ids[0] === q.correct) s.c++;
    else s.i++;
  }
  const subjects = (Object.keys(bySubject) as Array<keyof typeof bySubject>).map((subject) => {
    const s = bySubject[subject];
    return { subject, correct: s.c, incorrect: s.i, unanswered: s.u, total: s.t, percent: (s.c / s.t) * 100 };
  });
  const correct = subjects.reduce((a, s) => a + s.correct, 0);
  const incorrect = subjects.reduce((a, s) => a + s.incorrect, 0);
  const unanswered = subjects.reduce((a, s) => a + s.unanswered, 0);
  return { subjects, totals: { correct, incorrect, unanswered, total: QUESTIONS.length, score: correct * 2, maxScore: QUESTIONS.length * 2, percent: (correct / QUESTIONS.length) * 100 } };
}

function examSummary(db: MockDb) {
  const active = db.attempts.find((a) => a.status === 'in_progress');
  const done = db.attempts.find((a) => a.status !== 'in_progress');
  return {
    ...EXAM,
    totalQuestions: QUESTIONS.length,
    status: active ? 'in_progress' : done ? 'completed' : 'available',
    activeAttemptId: active?.id ?? null,
    resultId: done?.resultId ?? null,
    availableFrom: null,
  };
}

function resultPayload(db: MockDb, r: MockResult) {
  const attempt = db.attempts.find((a) => a.id === r.attemptId)!;
  const { subjects, totals } = score(attempt);
  return {
    id: r.id,
    attemptId: r.attemptId,
    examTitle: EXAM.title,
    completedAt: new Date(r.completedAt).toISOString(),
    finishReason: r.finishReason,
    totals,
    subjects,
    review: {
      enabled: true,
      items: QUESTIONS.map((q) => ({
        questionId: q.id,
        number: q.number,
        subject: q.subject,
        prompt: q.prompt,
        passage: q.passage,
        options: q.options,
        selectedOptionIds: attempt.answers[q.id]?.ids ?? [],
        correctOptionIds: [q.correct],
        explanation: q.explanation,
      })),
    },
  };
}

function route(method: string, path: string, body: Json, headers: AxiosHeaders): unknown {
  const db = load();
  sweep(db);
  const authed = () => {
    if (!db.studentId) throw new HttpError(401, 'UNAUTHENTICATED');
  };
  const out = (data: unknown) => {
    save(db);
    return data;
  };
  let match: RegExpMatchArray | null;

  /* ----- auth ----- */
  if (method === 'POST' && path === '/auth/jshshir') {
    if (body.jshshir !== DEMO_JSHSHIR) throw new HttpError(401, 'INVALID_CREDENTIALS');
    db.studentId = STUDENT.id;
    return out({ student: STUDENT });
  }
  if (method === 'POST' && path === '/auth/qr') {
    const token = String(body.token ?? '');
    if (token.startsWith('demo-qr-expired')) throw new HttpError(410, 'QR_EXPIRED');
    if (token.startsWith('demo-qr-used') || db.usedQr.includes(token)) throw new HttpError(409, 'QR_ALREADY_USED');
    if (!token.startsWith('demo-qr-valid')) throw new HttpError(401, 'QR_INVALID');
    db.usedQr.push(token); // single-use
    db.studentId = STUDENT.id;
    return out({ student: STUDENT });
  }
  if (method === 'GET' && path === '/auth/me') {
    authed();
    return out({ student: STUDENT });
  }
  if (method === 'POST' && path === '/auth/logout') {
    db.studentId = null;
    return out({ ok: true });
  }

  authed();

  /* ----- dashboard / results ----- */
  if (method === 'GET' && path === '/student/dashboard') {
    const completed = db.results.map((r) => resultPayload(db, r));
    const avg = (pick: (r: (typeof completed)[number]) => number) => (completed.length ? completed.reduce((a, r) => a + pick(r), 0) / completed.length : null);
    return out({
      student: { firstName: STUDENT.firstName },
      examinations: [examSummary(db)],
      stats: {
        totalExams: 1,
        completedExams: completed.length,
        overallPercent: avg((r) => r.totals.percent),
        subjects: (['math', 'iq', 'language'] as const).map((s) => ({ subject: s, percent: avg((r) => r.subjects.find((x) => x.subject === s)!.percent) })),
      },
      recentActivity: completed.slice(0, 5).map((r) => ({
        resultId: r.id,
        examTitle: r.examTitle,
        completedAt: r.completedAt,
        correct: r.totals.correct,
        total: r.totals.total,
        status: r.finishReason === 'timeout' ? 'expired' : 'completed',
      })),
    });
  }
  if (method === 'GET' && path === '/student/results') {
    return out({
      results: db.results.map((r) => {
        const p = resultPayload(db, r);
        return { id: p.id, examTitle: p.examTitle, completedAt: p.completedAt, correct: p.totals.correct, total: p.totals.total, percent: p.totals.percent };
      }),
    });
  }
  if (method === 'GET' && (match = path.match(/^\/student\/results\/([^/]+)$/))) {
    const r = db.results.find((x) => x.id === match![1]);
    if (!r) throw new HttpError(404, 'NOT_FOUND');
    return out(resultPayload(db, r));
  }

  /* ----- examinations ----- */
  if (method === 'GET' && path === '/examinations/available') return out({ examinations: [examSummary(db)] });

  if (method === 'POST' && (match = path.match(/^\/examinations\/([^/]+)\/start$/))) {
    if (match[1] !== EXAM.id) throw new HttpError(404, 'NOT_FOUND');
    const active = db.attempts.find((a) => a.status === 'in_progress');
    if (active) return out({ attemptId: active.id }); // one active attempt only
    if (db.attempts.some((a) => a.status !== 'in_progress')) throw new HttpError(409, 'ALREADY_COMPLETED');
    const now = Date.now();
    const attempt: MockAttempt = { id: uid('att'), examId: EXAM.id, status: 'in_progress', startedAt: now, expiresAt: now + DURATION_MS, answers: {}, submitKeys: [], resultId: null };
    db.attempts.push(attempt);
    return out({ attemptId: attempt.id });
  }

  const findAttempt = (id: string) => {
    const a = db.attempts.find((x) => x.id === id);
    if (!a) throw new HttpError(404, 'NOT_FOUND');
    return a;
  };

  if (method === 'GET' && (match = path.match(/^\/examinations\/attempts\/([^/]+)$/))) {
    const a = findAttempt(match[1]!);
    const answers: Answers = Object.fromEntries(Object.entries(a.answers).map(([k, v]) => [k, v.ids]));
    return out({
      id: a.id,
      examId: a.examId,
      examTitle: EXAM.title,
      status: a.status,
      startedAt: new Date(a.startedAt).toISOString(),
      expiresAt: new Date(a.expiresAt).toISOString(),
      serverTime: new Date().toISOString(),
      sections: EXAM.sections,
      questions: a.status === 'in_progress' ? publicQuestions() : [],
      answers,
      resultId: a.resultId,
    });
  }

  if (method === 'PUT' && (match = path.match(/^\/examinations\/attempts\/([^/]+)\/answers\/([^/]+)$/))) {
    const a = findAttempt(match[1]!);
    if (a.status !== 'in_progress' || Date.now() > a.expiresAt) throw new HttpError(409, 'ATTEMPT_CLOSED');
    const qid = match[2]!;
    const question = QUESTIONS.find((x) => x.id === qid);
    const ids = Array.isArray(body.selectedOptionIds) ? body.selectedOptionIds.map(String) : [];
    if (!question || !ids.every((id) => question.options.some((o) => o.id === id))) throw new HttpError(422, 'INVALID_ANSWER');
    const seq = Number(body.clientSeq) || 0;
    if ((a.answers[qid]?.seq ?? -1) <= seq) a.answers[qid] = { ids, seq }; // ignore stale writes
    return out({ questionId: qid, savedAt: new Date().toISOString() });
  }

  if (method === 'POST' && (match = path.match(/^\/examinations\/attempts\/([^/]+)\/submit$/))) {
    const a = findAttempt(match[1]!);
    const key = headers.get('Idempotency-Key');
    if (typeof key !== 'string' || !key) throw new HttpError(400, 'IDEMPOTENCY_KEY_REQUIRED');
    if (a.status === 'in_progress') {
      const withinGrace = Date.now() <= a.expiresAt + GRACE_MS;
      if (withinGrace && Array.isArray(body.unsavedAnswers)) {
        for (const u of body.unsavedAnswers as Array<{ questionId: string; selectedOptionIds: string[]; clientSeq: number }>) {
          if ((a.answers[u.questionId]?.seq ?? -1) <= u.clientSeq) a.answers[u.questionId] = { ids: u.selectedOptionIds, seq: u.clientSeq };
        }
      }
      finalize(db, a, Date.now() >= a.expiresAt || body.reason === 'timeout' ? 'timeout' : 'manual');
      a.submitKeys.push(key);
    }
    // Repeated submits (same or new key) return the same final state — never a second finalisation.
    return out({ attemptId: a.id, status: a.status, resultId: a.resultId });
  }

  /* ----- brain games (shared with the HTTP mock) ----- */
  try {
    const games = handleGames(db.games, { method, path, body, studentId: STUDENT.id, now: Date.now() });
    if (games) return out(games.data);
  } catch (e) {
    if (e instanceof GameApiError) throw new HttpError(e.status, e.code, e.message);
    throw e;
  }

  throw new HttpError(404, 'NOT_FOUND');
}

export function installMockBackend(instance: AxiosInstance): void {
  console.info('%c[mock] Bilimdon mock backend is active — development only', 'color:#17776a;font-weight:bold');
  instance.defaults.adapter = async (config: InternalAxiosRequestConfig): Promise<AxiosResponse> => {
    await new Promise((r) => setTimeout(r, 200 + Math.random() * 350));
    if (!navigator.onLine) throw new AxiosError('Network Error', AxiosError.ERR_NETWORK, config);

    const method = (config.method ?? 'get').toUpperCase();
    const path = (config.url ?? '').split('?')[0]!;
    const body = (typeof config.data === 'string' && config.data ? JSON.parse(config.data) : (config.data ?? {})) as Json;
    const headers = AxiosHeaders.from(config.headers);

    try {
      const data = route(method, path, body, headers);
      return { data, status: 200, statusText: 'OK', headers: {}, config };
    } catch (e) {
      if (e instanceof HttpError) {
        const response: AxiosResponse = { data: { code: e.code, message: e.message }, status: e.status, statusText: e.code, headers: {}, config };
        throw new AxiosError(e.message, AxiosError.ERR_BAD_REQUEST, config, null, response);
      }
      throw e;
    }
  };
}
