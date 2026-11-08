/**
 * Bilimdon — stateful mock backend (development only).
 *
 * Implements docs/api-contract.md over real HTTP on http://localhost:8000/api, so the frontend's
 * `npm run dev` proxy works exactly as it will against the real backend:
 *   - HttpOnly session cookie (no tokens in JS), login rate limiting, CSRF header check
 *   - QR tokens: random, short-lived, single-use; JSHSHIR is never returned
 *   - Exam attempts with server-side started_at / expires_at, deadline sweeper (finalises even
 *     if the browser never submits), clientSeq ordering for answers, idempotent submit
 *   - Scores computed only here
 *
 * Run:   npm run mock:api          (postman mock run …)
 *   or:  npm run mock:api:node     (plain node, same file)
 *
 * Env:   PORT=8000  MOCK_EXAM_SECONDS=3600  MOCK_GRACE_SECONDS=15  MOCK_FAIL_RATE=0  MOCK_REVIEW=1
 *
 * Demo accounts (JSHSHIR):
 *   12345678901234  Aziz    — fresh, exam available
 *   23456789012345  Malika  — fresh, exam available
 *   34567890123456  Bobur   — exam already completed (has a result + history)
 * Demo QR tokens: demo-qr-valid-7f3a9c2e1b4d (Aziz, single-use), demo-qr-expired-0c8e2a9f71, demo-qr-used-5b1d7e3c9a20
 * Dev helpers:    POST /api/dev/qr-tokens {"jshshir":"…"} → fresh random token (5 min)   ·   POST /api/dev/reset
 */
const http = require('http');
const crypto = require('crypto');
const QUESTIONS = require('./data/questions.json');
// Brain games backend logic, built from src/mocks/games/gameServer.ts by `npm run mock:data`.
const games = require('./lib/games.cjs');

const PORT = Number(process.env.PORT) || 8000;
const EXAM_MS = (Number(process.env.MOCK_EXAM_SECONDS) || 3600) * 1000;
const GRACE_MS = (Number(process.env.MOCK_GRACE_SECONDS) || 15) * 1000;
const FAIL_RATE = Math.min(1, Math.max(0, Number(process.env.MOCK_FAIL_RATE) || 0));
const REVIEW_ENABLED = process.env.MOCK_REVIEW !== '0';
const SESSION_TTL_MS = 8 * 60 * 60 * 1000;
const QR_TTL_MS = 5 * 60 * 1000;
const COOKIE = 'bilimdon_sid';
const JSON_HEADER = { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' };

const EXAM = {
  id: 'exam-autumn-2026',
  title: 'Kuzgi bilimlar imtihoni',
  description: 'Matematika, mantiq va ona tili bo‘yicha 45 ta qiziqarli savol.',
  durationMinutes: Math.round(EXAM_MS / 60000) || 1,
  sections: [
    { subject: 'math', title: 'Matematika', questionCount: QUESTIONS.filter((q) => q.subject === 'math').length },
    { subject: 'iq', title: 'Mantiq (IQ)', questionCount: QUESTIONS.filter((q) => q.subject === 'iq').length },
    { subject: 'language', title: 'Ona tili va adabiyot', questionCount: QUESTIONS.filter((q) => q.subject === 'language').length },
  ],
};

// JSHSHIR lives only here (server side). It is never sent back to the client.
const STUDENTS = [
  { id: 'stu_aziz', jshshir: '12345678901234', firstName: 'Aziz', lastName: 'Karimov', className: '6-“B” sinf', schoolName: '12-maktab', photoUrl: null },
  { id: 'stu_malika', jshshir: '23456789012345', firstName: 'Malika', lastName: 'Yusupova', className: '5-“A” sinf', schoolName: '7-maktab', photoUrl: null },
  { id: 'stu_bobur', jshshir: '34567890123456', firstName: 'Bobur', lastName: 'Aliyev', className: '7-“V” sinf', schoolName: '12-maktab', photoUrl: null },
];
const publicStudent = ({ jshshir: _omit, ...s }) => s;

/* ------------------------------------------------------------------ state */

// Uses Postman mock state when running under `postman mock run` / cloud, otherwise in-memory.
const memory = new Map();
const hasPm = typeof pm !== 'undefined' && pm && pm.state;
const store = {
  get: async (k) => (hasPm ? pm.state.get(k) : memory.get(k)),
  set: async (k, v) => (hasPm ? pm.state.set(k, v) : void memory.set(k, v)),
};

// Serialise all state mutations: answers arrive in parallel and must not overwrite each other.
let lock = Promise.resolve();
function withDb(fn) {
  const run = lock.then(async () => {
    const db = (await store.get('db')) || seed();
    if (!db.games) db.games = games.createGamesState(); // state saved by an older mock version
    const result = await fn(db);
    await store.set('db', db);
    return result;
  });
  lock = run.catch(() => undefined);
  return run;
}

function seed() {
  const now = Date.now();
  const db = {
    sessions: {},
    qrTokens: {
      'demo-qr-valid-7f3a9c2e1b4d': { studentId: 'stu_aziz', expiresAt: now + 365 * 864e5, usedAt: null },
      'demo-qr-expired-0c8e2a9f71': { studentId: 'stu_aziz', expiresAt: now - 60_000, usedAt: null },
      'demo-qr-used-5b1d7e3c9a20': { studentId: 'stu_aziz', expiresAt: now + 365 * 864e5, usedAt: now - 3600_000 },
    },
    attempts: [],
    results: [],
    games: games.createGamesState(),
  };
  games.seedGameHistory(db.games, 'stu_bobur', now);
  // Bobur already finished the exam yesterday — gives history/results something real to show.
  const started = now - 864e5;
  const answers = {};
  QUESTIONS.forEach((q, i) => {
    if (i % 7 === 6) return; // a few unanswered
    const wrong = q.options.find((o) => o.id !== q.correct).id;
    answers[q.id] = { ids: [i % 4 === 3 ? wrong : q.correct], seq: started + i };
  });
  const attempt = { id: 'att_seed_bobur', studentId: 'stu_bobur', examId: EXAM.id, status: 'submitted', startedAt: started, expiresAt: started + EXAM_MS, answers, submitKeys: [], resultId: 'res_seed_bobur' };
  db.attempts.push(attempt);
  db.results.push({ id: 'res_seed_bobur', attemptId: attempt.id, studentId: 'stu_bobur', completedAt: started + 41 * 60_000, finishReason: 'manual' });
  return db;
}

/* ------------------------------------------------------------------ domain */

const rid = (prefix) => `${prefix}_${crypto.randomBytes(9).toString('base64url')}`;

class HttpError extends Error {
  constructor(status, code, message) {
    super(message || code);
    this.status = status;
    this.code = code;
  }
}

function finalize(db, attempt, reason) {
  if (attempt.status !== 'in_progress') return;
  attempt.status = reason === 'timeout' ? 'expired' : 'submitted';
  const result = { id: rid('res'), attemptId: attempt.id, studentId: attempt.studentId, completedAt: Math.min(Date.now(), attempt.expiresAt), finishReason: reason };
  db.results.unshift(result);
  attempt.resultId = result.id;
}

/** Deadline policy: past expires_at + grace, the server finalises on its own. */
function sweep(db) {
  const now = Date.now();
  for (const a of db.attempts) if (a.status === 'in_progress' && now > a.expiresAt + GRACE_MS) finalize(db, a, 'timeout');
  for (const [sid, s] of Object.entries(db.sessions)) if (now - s.createdAt > SESSION_TTL_MS) delete db.sessions[sid];
}

function score(attempt) {
  const by = {};
  for (const q of QUESTIONS) {
    const s = (by[q.subject] ||= { correct: 0, incorrect: 0, unanswered: 0, total: 0 });
    s.total++;
    const ids = (attempt.answers[q.id] && attempt.answers[q.id].ids) || [];
    if (ids.length === 0) s.unanswered++;
    else if (ids.length === 1 && ids[0] === q.correct) s.correct++;
    else s.incorrect++;
  }
  const subjects = ['math', 'iq', 'language'].filter((k) => by[k]).map((subject) => ({ subject, ...by[subject], percent: (by[subject].correct / by[subject].total) * 100 }));
  const sum = (k) => subjects.reduce((a, s) => a + s[k], 0);
  const total = QUESTIONS.length;
  return {
    subjects,
    totals: { correct: sum('correct'), incorrect: sum('incorrect'), unanswered: sum('unanswered'), total, score: sum('correct') * 2, maxScore: total * 2, percent: (sum('correct') / total) * 100 },
  };
}

function resultPayload(db, r) {
  const attempt = db.attempts.find((a) => a.id === r.attemptId);
  const { subjects, totals } = score(attempt);
  return {
    id: r.id,
    attemptId: r.attemptId,
    examTitle: EXAM.title,
    completedAt: new Date(r.completedAt).toISOString(),
    finishReason: r.finishReason,
    totals,
    subjects,
    review: REVIEW_ENABLED
      ? {
          enabled: true,
          items: QUESTIONS.map((q) => ({
            questionId: q.id,
            number: q.number,
            subject: q.subject,
            prompt: q.prompt,
            passage: q.passage,
            options: q.options,
            selectedOptionIds: (attempt.answers[q.id] && attempt.answers[q.id].ids) || [],
            correctOptionIds: [q.correct],
            explanation: q.explanation,
          })),
        }
      : { enabled: false },
  };
}

const publicQuestions = () => QUESTIONS.map(({ correct: _c, explanation: _e, ...q }) => q);

function examSummary(db, studentId) {
  const mine = db.attempts.filter((a) => a.studentId === studentId && a.examId === EXAM.id);
  const active = mine.find((a) => a.status === 'in_progress');
  const done = mine.find((a) => a.status !== 'in_progress');
  return {
    ...EXAM,
    totalQuestions: QUESTIONS.length,
    status: active ? 'in_progress' : done ? 'completed' : 'available',
    activeAttemptId: active ? active.id : null,
    resultId: done ? done.resultId : null,
    availableFrom: null,
  };
}

/* ------------------------------------------------------------------ http helpers */

const rate = new Map(); // ip → timestamps (login attempts)
function rateLimited(ip) {
  const now = Date.now();
  const hits = (rate.get(ip) || []).filter((t) => now - t < 60_000);
  hits.push(now);
  rate.set(ip, hits);
  return hits.length > 10;
}

function parseCookies(header) {
  return Object.fromEntries(
    (header || '')
      .split(';')
      .map((p) => p.trim().split('='))
      .filter(([k]) => k)
      .map(([k, ...v]) => [k, decodeURIComponent(v.join('='))]),
  );
}

// `Secure` is omitted only because this mock runs on plain http://localhost. The real backend MUST set it.
const sessionCookie = (sid) => `${COOKIE}=${sid}; HttpOnly; Path=/; SameSite=Lax; Max-Age=${SESSION_TTL_MS / 1000}`;
const clearCookie = () => `${COOKIE}=; HttpOnly; Path=/; SameSite=Lax; Max-Age=0`;

function readJson(req) {
  return new Promise((resolve) => {
    let raw = '';
    req.on('data', (c) => {
      raw += c;
      if (raw.length > 1e6) req.destroy();
    });
    req.on('end', () => {
      try {
        const parsed = raw ? JSON.parse(raw) : {};
        resolve(parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {});
      } catch {
        resolve({});
      }
    });
  });
}

function send(res, status, data, headers = {}) {
  res.writeHead(status, { ...JSON_HEADER, ...headers });
  res.end(JSON.stringify(data));
}

/* ------------------------------------------------------------------ routes */

async function handle(req, body) {
  const method = req.method;
  const path = (req.url || '').split('?')[0].replace(/\/+$/, '');
  const ip = req.socket.remoteAddress || 'local';
  const cookies = parseCookies(req.headers.cookie);
  const mutating = method !== 'GET' && method !== 'HEAD';

  if (mutating && req.headers['x-requested-with'] !== 'XMLHttpRequest') throw new HttpError(403, 'CSRF_CHECK_FAILED', 'Missing X-Requested-With header');

  return withDb((db) => {
    sweep(db);
    const session = db.sessions[cookies[COOKIE]];
    const student = session && STUDENTS.find((s) => s.id === session.studentId);
    let m;

    const login = (s) => {
      const sid = crypto.randomBytes(32).toString('base64url');
      db.sessions[sid] = { studentId: s.id, createdAt: Date.now() };
      return { status: 200, data: { student: publicStudent(s) }, headers: { 'Set-Cookie': sessionCookie(sid) } };
    };

    /* ---- auth ---- */
    // @endpoint POST /api/auth/jshshir
    if (method === 'POST' && path === '/api/auth/jshshir') {
      if (rateLimited(ip)) throw new HttpError(429, 'RATE_LIMITED');
      const jshshir = String(body.jshshir || '');
      if (!/^\d{14}$/.test(jshshir)) throw new HttpError(422, 'VALIDATION_ERROR', 'jshshir must be 14 digits');
      const s = STUDENTS.find((x) => x.jshshir === jshshir);
      if (!s) throw new HttpError(401, 'INVALID_CREDENTIALS');
      return login(s);
    }

    // @endpoint POST /api/auth/qr
    if (method === 'POST' && path === '/api/auth/qr') {
      if (rateLimited(ip)) throw new HttpError(429, 'RATE_LIMITED');
      const entry = db.qrTokens[String(body.token || '')];
      if (!entry) throw new HttpError(401, 'QR_INVALID');
      if (entry.usedAt) throw new HttpError(409, 'QR_ALREADY_USED');
      if (Date.now() > entry.expiresAt) throw new HttpError(410, 'QR_EXPIRED');
      entry.usedAt = Date.now(); // consumed atomically (we're inside the db lock)
      return login(STUDENTS.find((x) => x.id === entry.studentId));
    }

    // @endpoint GET /api/auth/me
    if (method === 'GET' && path === '/api/auth/me') {
      if (!student) throw new HttpError(401, 'UNAUTHENTICATED');
      return { status: 200, data: { student: publicStudent(student) } };
    }

    // @endpoint POST /api/auth/logout
    if (method === 'POST' && path === '/api/auth/logout') {
      delete db.sessions[cookies[COOKIE]];
      return { status: 200, data: { ok: true }, headers: { 'Set-Cookie': clearCookie() } };
    }

    /* ---- dev helpers (would not exist on the real backend) ---- */
    // @endpoint POST /api/dev/qr-tokens
    if (method === 'POST' && path === '/api/dev/qr-tokens') {
      const s = STUDENTS.find((x) => x.jshshir === String(body.jshshir || '')) || STUDENTS[0];
      const token = crypto.randomBytes(24).toString('base64url');
      db.qrTokens[token] = { studentId: s.id, expiresAt: Date.now() + QR_TTL_MS, usedAt: null };
      return { status: 201, data: { token, studentId: s.id, expiresAt: new Date(Date.now() + QR_TTL_MS).toISOString() } };
    }
    // @endpoint POST /api/dev/reset
    if (method === 'POST' && path === '/api/dev/reset') {
      Object.assign(db, seed());
      rate.clear();
      return { status: 200, data: { ok: true } };
    }

    if (!path.startsWith('/api/')) throw new HttpError(404, 'NOT_FOUND');
    if (!student) throw new HttpError(401, 'UNAUTHENTICATED');
    const sid = student.id;

    /* ---- dashboard & results ---- */
    // @endpoint GET /api/student/dashboard
    if (method === 'GET' && path === '/api/student/dashboard') {
      const results = db.results.filter((r) => r.studentId === sid).map((r) => resultPayload(db, r));
      const avg = (pick) => (results.length ? results.reduce((a, r) => a + pick(r), 0) / results.length : null);
      return {
        status: 200,
        data: {
          student: { firstName: student.firstName },
          examinations: [examSummary(db, sid)],
          stats: {
            totalExams: 1,
            completedExams: results.length,
            overallPercent: avg((r) => r.totals.percent),
            subjects: ['math', 'iq', 'language'].map((subject) => ({ subject, percent: avg((r) => r.subjects.find((x) => x.subject === subject).percent) })),
          },
          recentActivity: results.slice(0, 5).map((r) => ({
            resultId: r.id,
            examTitle: r.examTitle,
            completedAt: r.completedAt,
            correct: r.totals.correct,
            total: r.totals.total,
            status: r.finishReason === 'timeout' ? 'expired' : 'completed',
          })),
        },
      };
    }

    // @endpoint GET /api/student/profile
    if (method === 'GET' && path === '/api/student/profile') return { status: 200, data: { student: publicStudent(student) } };

    // @endpoint GET /api/student/results
    if (method === 'GET' && path === '/api/student/results') {
      const results = db.results
        .filter((r) => r.studentId === sid)
        .map((r) => {
          const p = resultPayload(db, r);
          return { id: p.id, examTitle: p.examTitle, completedAt: p.completedAt, correct: p.totals.correct, total: p.totals.total, percent: p.totals.percent };
        });
      return { status: 200, data: { results } };
    }

    // @endpoint GET /api/student/results/:resultId
    if (method === 'GET' && (m = path.match(/^\/api\/student\/results\/([^/]+)$/))) {
      const r = db.results.find((x) => x.id === m[1]);
      if (!r || r.studentId !== sid) throw new HttpError(404, 'NOT_FOUND'); // never reveal other students' results
      return { status: 200, data: resultPayload(db, r) };
    }

    /* ---- examinations ---- */
    // @endpoint GET /api/examinations/available
    if (method === 'GET' && path === '/api/examinations/available') return { status: 200, data: { examinations: [examSummary(db, sid)] } };

    // @endpoint POST /api/examinations/:examId/start
    if (method === 'POST' && (m = path.match(/^\/api\/examinations\/([^/]+)\/start$/))) {
      if (m[1] !== EXAM.id) throw new HttpError(404, 'NOT_FOUND');
      const mine = db.attempts.filter((a) => a.studentId === sid && a.examId === EXAM.id);
      const active = mine.find((a) => a.status === 'in_progress');
      if (active) return { status: 200, data: { attemptId: active.id } }; // one active attempt only
      if (mine.length > 0) throw new HttpError(409, 'ALREADY_COMPLETED');
      const now = Date.now();
      const attempt = { id: rid('att'), studentId: sid, examId: EXAM.id, status: 'in_progress', startedAt: now, expiresAt: now + EXAM_MS, answers: {}, submitKeys: [], resultId: null };
      db.attempts.push(attempt);
      return { status: 201, data: { attemptId: attempt.id } };
    }

    const ownAttempt = (id) => {
      const a = db.attempts.find((x) => x.id === id);
      if (!a || a.studentId !== sid) throw new HttpError(404, 'NOT_FOUND');
      return a;
    };

    // @endpoint GET /api/examinations/attempts/:attemptId
    if (method === 'GET' && (m = path.match(/^\/api\/examinations\/attempts\/([^/]+)$/))) {
      const a = ownAttempt(m[1]);
      return {
        status: 200,
        data: {
          id: a.id,
          examId: a.examId,
          examTitle: EXAM.title,
          status: a.status,
          startedAt: new Date(a.startedAt).toISOString(),
          expiresAt: new Date(a.expiresAt).toISOString(),
          serverTime: new Date().toISOString(),
          sections: EXAM.sections,
          questions: a.status === 'in_progress' ? publicQuestions() : [],
          answers: Object.fromEntries(Object.entries(a.answers).map(([k, v]) => [k, v.ids])),
          resultId: a.resultId,
        },
      };
    }

    // @endpoint PUT /api/examinations/attempts/:attemptId/answers/:questionId
    if (method === 'PUT' && (m = path.match(/^\/api\/examinations\/attempts\/([^/]+)\/answers\/([^/]+)$/))) {
      const a = ownAttempt(m[1]);
      if (FAIL_RATE > 0 && Math.random() < FAIL_RATE) throw new HttpError(503, 'TEMPORARILY_UNAVAILABLE', 'Simulated failure (MOCK_FAIL_RATE)');
      if (a.status !== 'in_progress' || Date.now() > a.expiresAt) throw new HttpError(409, 'ATTEMPT_CLOSED');
      const q = QUESTIONS.find((x) => x.id === m[2]);
      const ids = Array.isArray(body.selectedOptionIds) ? body.selectedOptionIds.map(String) : null;
      const seq = Number(body.clientSeq);
      if (!q || !ids || ids.length > 1 || !Number.isFinite(seq) || !ids.every((id) => q.options.some((o) => o.id === id))) throw new HttpError(422, 'INVALID_ANSWER');
      const prev = a.answers[q.id];
      if (!prev || prev.seq <= seq) a.answers[q.id] = { ids, seq }; // ignore stale (out-of-order) writes
      return { status: 200, data: { questionId: q.id, savedAt: new Date().toISOString() } };
    }

    // @endpoint POST /api/examinations/attempts/:attemptId/submit
    if (method === 'POST' && (m = path.match(/^\/api\/examinations\/attempts\/([^/]+)\/submit$/))) {
      const a = ownAttempt(m[1]);
      const key = req.headers['idempotency-key'];
      if (!key || typeof key !== 'string') throw new HttpError(400, 'IDEMPOTENCY_KEY_REQUIRED');
      if (a.status === 'in_progress') {
        if (Date.now() <= a.expiresAt + GRACE_MS && Array.isArray(body.unsavedAnswers)) {
          for (const u of body.unsavedAnswers) {
            const q = QUESTIONS.find((x) => x.id === u.questionId);
            const ids = Array.isArray(u.selectedOptionIds) ? u.selectedOptionIds.map(String) : [];
            if (!q || ids.length > 1 || !ids.every((id) => q.options.some((o) => o.id === id))) continue;
            const prev = a.answers[q.id];
            if (!prev || prev.seq <= Number(u.clientSeq)) a.answers[q.id] = { ids, seq: Number(u.clientSeq) };
          }
        }
        finalize(db, a, Date.now() >= a.expiresAt || body.reason === 'timeout' ? 'timeout' : 'manual');
        a.submitKeys.push(key);
      }
      // Repeats return the same final state; an attempt is never finalised twice.
      return { status: 200, data: { attemptId: a.id, status: a.status, resultId: a.resultId } };
    }

    /* ---- brain games (Bilimlar laboratoriyasi) ---- */
    // @endpoint GET /api/games, /api/games/categories, /api/games/:slug, /api/games/daily-challenge
    // @endpoint POST /api/games/:id/start, /api/games/sessions/:id/answer, /api/games/sessions/:id/complete
    // @endpoint GET /api/games/sessions/:id/result, /api/student/games/statistics, /api/student/achievements
    try {
      const r = games.handleGames(db.games, { method, path: path.slice('/api'.length), body, studentId: sid, now: Date.now() });
      if (r) return r;
    } catch (e) {
      if (e && e.isGameApiError) throw new HttpError(e.status, e.code, e.message);
      throw e;
    }

    throw new HttpError(404, 'NOT_FOUND', `No mock route for ${method} ${path}`);
  });
}

const server = http.createServer(async (req, res) => {
  const body = readJson(req); // attach listeners before any await
  const started = Date.now();
  try {
    await new Promise((r) => setTimeout(r, 120 + Math.random() * 230)); // realistic latency
    const { status, data, headers } = await handle(req, await body);
    send(res, status, data, headers);
  } catch (e) {
    const status = e instanceof HttpError ? e.status : 500;
    if (!(e instanceof HttpError)) console.error(e);
    send(res, status, { code: e.code || 'INTERNAL_ERROR', message: e.message || 'Internal error' });
  } finally {
    // Never log request bodies (they may contain JSHSHIR).
    console.log(`${req.method} ${(req.url || '').split('?')[0]} → ${res.statusCode} (${Date.now() - started}ms)`);
  }
});

// Deadline sweeper: finalises expired attempts even when no client is connected.
setInterval(() => void withDb((db) => sweep(db)).catch(() => undefined), 5000).unref();

server.listen(PORT, () => console.log(`Bilimdon mock API on http://localhost:${PORT}/api  (exam ${EXAM_MS / 1000}s, grace ${GRACE_MS / 1000}s, fail-rate ${FAIL_RATE})`));
