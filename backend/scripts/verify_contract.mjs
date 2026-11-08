/**
 * Checks the running backend against the frontend's own zod schemas, the contract's source of truth
 * (frontend/docs/api-contract.md). If a field is renamed on either side, this fails.
 *
 *   python manage.py seed_demo --reset     # needs fresh demo data
 *   python manage.py runserver             # in another terminal
 *   node scripts/verify_contract.mjs       # needs `npm install` to have run in frontend/
 */
import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const API = process.env.API_URL ?? 'http://127.0.0.1:8000/api';
const frontend = resolve(dirname(fileURLToPath(import.meta.url)), '../../frontend');

// Load Vite from the frontend's node_modules, and let it compile the TypeScript schema files.
const require = createRequire(resolve(frontend, 'package.json'));
const vitePath = resolve(dirname(require.resolve('vite/package.json')), 'dist/node/index.js');
const { createServer } = await import(pathToFileURL(vitePath).href);
const vite = await createServer({
  root: frontend,
  logLevel: 'error',
  server: { middlewareMode: true, hmr: false },
  appType: 'custom',
});

let passed = 0;
const failures = [];

function record(name, problem) {
  if (problem) {
    failures.push(`${name}: ${problem}`);
    console.log(`  FAIL ${name}\n       ${problem}`);
  } else {
    passed += 1;
    console.log(`  ok   ${name}`);
  }
}

/** A tiny client that keeps the session cookie, as a browser would. */
function newClient() {
  let cookie = '';
  return async function call(method, path, body, headers = {}) {
    const response = await fetch(`${API}${path}`, {
      method,
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
        ...(cookie ? { Cookie: cookie } : {}),
        ...headers,
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    const setCookie = response.headers.get('set-cookie');
    if (setCookie) cookie = setCookie.split(';')[0];
    const text = await response.text();
    return { status: response.status, data: text ? JSON.parse(text) : null };
  };
}

const check = (name, schema, response, expectedStatus = 200) => {
  if (response.status !== expectedStatus) {
    record(name, `HTTP ${response.status}, expected ${expectedStatus}: ${JSON.stringify(response.data)}`);
    return response.data;
  }
  const parsed = schema.safeParse(response.data);
  record(name, parsed.success ? null : JSON.stringify(parsed.error.issues.slice(0, 3)));
  return response.data;
};

const expectError = (name, response, status, code) =>
  record(
    name,
    response.status === status && response.data?.code === code && typeof response.data?.message === 'string'
      ? null
      : `got HTTP ${response.status} ${JSON.stringify(response.data)}`,
  );

try {
  const { z } = await vite.ssrLoadModule('zod');
  const auth = await vite.ssrLoadModule('/src/features/auth/types/index.ts');
  const dashboard = await vite.ssrLoadModule('/src/features/dashboard/types/index.ts');
  const exams = await vite.ssrLoadModule('/src/features/examination/types/index.ts');
  const results = await vite.ssrLoadModule('/src/features/results/types/index.ts');
  const games = await vite.ssrLoadModule('/src/features/brain-games/types/index.ts');

  console.log('\nAuth');
  const aziz = newClient();
  expectError('me without a session is 401', await aziz('GET', '/auth/me'), 401, 'UNAUTHENTICATED');
  expectError(
    'wrong JSHSHIR',
    await aziz('POST', '/auth/jshshir', { jshshir: '99999999999999' }),
    401,
    'INVALID_CREDENTIALS',
  );
  check(
    'POST /auth/jshshir',
    auth.authResponseSchema,
    await aziz('POST', '/auth/jshshir', { jshshir: '12345678901234' }),
  );
  check('GET /auth/me', auth.authResponseSchema, await aziz('GET', '/auth/me'));

  const qr = newClient();
  expectError('expired QR', await qr('POST', '/auth/qr', { token: 'demo-qr-expired-0c8e2a9f71' }), 410, 'QR_EXPIRED');
  expectError('used QR', await qr('POST', '/auth/qr', { token: 'demo-qr-used-5b1d7e3c9a20' }), 409, 'QR_ALREADY_USED');
  expectError('unknown QR', await qr('POST', '/auth/qr', { token: 'unknown-token-abcdefgh' }), 401, 'QR_INVALID');
  check('POST /auth/qr', auth.authResponseSchema, await qr('POST', '/auth/qr', { token: 'demo-qr-valid-7f3a9c2e1b4d' }));
  check('POST /auth/logout', z.object({ ok: z.literal(true) }), await qr('POST', '/auth/logout'));

  console.log('\nDashboard and exam');
  const board = check('GET /student/dashboard', dashboard.dashboardSchema, await aziz('GET', '/student/dashboard'));
  const listed = check(
    'GET /examinations/available',
    z.object({ examinations: z.array(exams.examSummarySchema) }),
    await aziz('GET', '/examinations/available'),
  );
  const examId = listed.examinations[0].id;
  const started = check('POST /examinations/{id}/start', exams.startAttemptResponseSchema, await aziz('POST', `/examinations/${examId}/start`), 201);
  const attemptId = started.attemptId;
  const attempt = check('GET /examinations/attempts/{id}', exams.attemptSessionSchema, await aziz('GET', `/examinations/attempts/${attemptId}`));
  record('dashboard exam was available before starting', board.examinations[0].status === 'available' ? null : board.examinations[0].status);
  record(
    'exam payload has no answers or explanations',
    /isCorrect|correct|explanation/i.test(JSON.stringify(attempt.questions)) ? 'leak found' : null,
  );

  const [q1, q2] = attempt.questions;
  const seq = Date.now();
  check(
    'PUT .../answers/{questionId} with a millisecond clientSeq',
    exams.saveAnswerResponseSchema,
    await aziz('PUT', `/examinations/attempts/${attemptId}/answers/${q1.id}`, { selectedOptionIds: [q1.options[0].id], clientSeq: seq }),
  );
  expectError(
    'unknown option id is 422',
    await aziz('PUT', `/examinations/attempts/${attemptId}/answers/${q1.id}`, { selectedOptionIds: ['nope'], clientSeq: seq + 1 }),
    422,
    'INVALID_ANSWER',
  );

  const submitted = check(
    'POST .../submit',
    exams.submitResponseSchema,
    await aziz(
      'POST',
      `/examinations/attempts/${attemptId}/submit`,
      { reason: 'manual', unsavedAnswers: [{ questionId: q2.id, selectedOptionIds: [q2.options[1].id], clientSeq: seq }] },
      { 'Idempotency-Key': 'contract-check-1' },
    ),
  );
  const repeated = await aziz('POST', `/examinations/attempts/${attemptId}/submit`, { reason: 'manual', unsavedAnswers: [] }, { 'Idempotency-Key': 'contract-check-2' });
  record('submit is idempotent', repeated.data.resultId === submitted.resultId ? null : 'different result');
  expectError('start after finishing', await aziz('POST', `/examinations/${examId}/start`), 409, 'ALREADY_COMPLETED');
  expectError(
    'answer after finishing',
    await aziz('PUT', `/examinations/attempts/${attemptId}/answers/${q1.id}`, { selectedOptionIds: [], clientSeq: seq + 2 }),
    409,
    'ATTEMPT_CLOSED',
  );

  console.log('\nResults');
  check('GET /examinations/attempts/{id} when closed', exams.attemptSessionSchema, await aziz('GET', `/examinations/attempts/${attemptId}`));
  check('GET /student/results', z.object({ results: z.array(results.resultSummarySchema) }), await aziz('GET', '/student/results'));
  const result = check('GET /student/results/{id}', results.examResultSchema, await aziz('GET', `/student/results/${submitted.resultId}`));
  record('review has items', result.review.enabled && result.review.items?.length === 45 ? null : 'expected 45 review items');
  check('GET /student/dashboard with a result', dashboard.dashboardSchema, await aziz('GET', '/student/dashboard'));

  const malika = newClient();
  await malika('POST', '/auth/jshshir', { jshshir: '23456789012345' });
  expectError('another student gets 404 for a result', await malika('GET', `/student/results/${submitted.resultId}`), 404, 'NOT_FOUND');
  expectError('another student gets 404 for an attempt', await malika('GET', `/examinations/attempts/${attemptId}`), 404, 'NOT_FOUND');

  console.log('\nBrain games');
  const list = check('GET /games', z.object({ games: z.array(games.gameSchema) }), await aziz('GET', '/games'));
  check('GET /games/categories', z.object({ categories: z.array(games.gameCategoryInfoSchema) }), await aziz('GET', '/games/categories'));
  check('GET /games/{slug}', z.object({ game: games.gameSchema }), await aziz('GET', '/games/naqsh-ustasi'));
  const daily = check('GET /games/daily-challenge', games.dailyChallengeSchema, await aziz('GET', '/games/daily-challenge'));
  const inactive = list.games.find((game) => !game.isActive);
  expectError('inactive game', await aziz('POST', `/games/${inactive.id}/start`, { difficulty: 'easy', daily: false }), 409, 'GAME_NOT_AVAILABLE');

  const dailyQuestion = check('GET /games/daily-question', games.dailyQuestionSchema, await aziz('GET', '/games/daily-question'));
  check(
    'POST /games/daily-question/answer',
    games.dailyQuestionSchema,
    await aziz('POST', '/games/daily-question/answer', { questionId: dailyQuestion.question.id, optionId: dailyQuestion.question.options[0].id }),
  );

  // Every playable game at every level, across several rounds, so random content gets covered.
  for (const game of list.games.filter((item) => item.isActive)) {
    for (const difficulty of game.difficulties) {
      for (let round = 0; round < 3; round += 1) {
        const label = `${game.slug} ${difficulty}`;
        const response = await aziz('POST', `/games/${game.id}/start`, { difficulty, daily: false });
        const parsed = games.startGameResponseSchema.safeParse(response.data);
        if (response.status !== 201 || !parsed.success) {
          record(`start ${label}`, JSON.stringify(parsed.error?.issues?.slice(0, 3) ?? response.data));
        }
      }
      const start = check(`POST /games/{id}/start (${game.slug}, ${difficulty})`, games.startGameResponseSchema, await aziz('POST', `/games/${game.id}/start`, { difficulty, daily: false }), 201);
      const sessionId = start.session.id;
      let evidence = {};
      if (start.content.kind === 'memory') {
        const faces = new Map();
        for (const card of start.content.cards) faces.set(card.face, [...(faces.get(card.face) ?? []), card.id]);
        evidence = { moves: [...faces.values()] };
        expectError(`claiming a memory win (${difficulty})`, await aziz('POST', `/games/sessions/${sessionId}/complete`, { moves: [] }, { 'Idempotency-Key': 'x' }), 422, 'INVALID_MOVES');
      } else {
        const question = start.content.questions[0];
        check(
          `POST .../answer (${game.slug}, ${difficulty})`,
          games.answerResponseSchema,
          await aziz('POST', `/games/sessions/${sessionId}/answer`, { questionId: question.id, optionId: question.options[0].id }),
        );
      }
      check(`GET /games/sessions/{id} (${game.slug}, ${difficulty})`, games.resumeGameResponseSchema, await aziz('GET', `/games/sessions/${sessionId}`));
      const finished = check(`POST .../complete (${game.slug}, ${difficulty})`, games.gameResultSchema, await aziz('POST', `/games/sessions/${sessionId}/complete`, evidence, { 'Idempotency-Key': `${sessionId}-complete` }));
      const again = await aziz('POST', `/games/sessions/${sessionId}/complete`, evidence, { 'Idempotency-Key': `${sessionId}-complete` });
      record(`complete is idempotent (${game.slug}, ${difficulty})`, JSON.stringify(again.data) === JSON.stringify(finished) ? null : 'responses differ');
      check(`GET .../result (${game.slug}, ${difficulty})`, games.gameResultSchema, await aziz('GET', `/games/sessions/${sessionId}/result`));
      expectError(`resume after completing (${difficulty})`, await aziz('GET', `/games/sessions/${sessionId}`), 409, 'SESSION_COMPLETED');
    }
  }

  const left = await aziz('POST', `/games/${list.games[1].id}/start`, { difficulty: 'easy', daily: false });
  check('POST .../abandon', z.object({ session: games.gameSessionSchema }), await aziz('POST', `/games/sessions/${left.data.session.id}/abandon`));
  expectError('another student gets 404 for a session', await malika('GET', `/games/sessions/${left.data.session.id}`), 404, 'SESSION_NOT_FOUND');

  console.log('\nDaily challenge, statistics, achievements');
  const dailyStart = check(
    'POST /games/{id}/start (daily)',
    games.startGameResponseSchema,
    await aziz('POST', `/games/${daily.game.id}/start`, { difficulty: daily.difficulty, daily: true }),
    201,
  );
  record('session is marked as daily', dailyStart.session.isDaily ? null : 'isDaily is false');
  let dailyEvidence = {};
  if (dailyStart.content.kind === 'memory') {
    const faces = new Map();
    for (const card of dailyStart.content.cards) faces.set(card.face, [...(faces.get(card.face) ?? []), card.id]);
    dailyEvidence = { moves: [...faces.values()] };
  }
  const dailyResult = check('complete daily session', games.gameResultSchema, await aziz('POST', `/games/sessions/${dailyStart.session.id}/complete`, dailyEvidence, { 'Idempotency-Key': 'daily' }));
  record('daily bonus granted', dailyResult.bonus === 20 ? null : `bonus = ${dailyResult.bonus}`);
  check(
    'POST /games/daily-challenge/complete',
    z.object({ date: z.string(), completed: z.literal(true), completedAt: z.string() }),
    await aziz('POST', '/games/daily-challenge/complete', { sessionId: dailyStart.session.id }),
  );
  check('GET /student/games/statistics', games.gameStatisticsSchema, await aziz('GET', '/student/games/statistics'));
  check('GET /student/achievements', z.object({ achievements: z.array(games.achievementSchema) }), await aziz('GET', '/student/achievements'));

  console.log('\nDemo student with history');
  const bobur = newClient();
  await bobur('POST', '/auth/jshshir', { jshshir: '34567890123456' });
  const boburBoard = check('dashboard of a student with a finished exam', dashboard.dashboardSchema, await bobur('GET', '/student/dashboard'));
  record('finished exam shows as completed', boburBoard.examinations[0].status === 'completed' ? null : boburBoard.examinations[0].status);
  check('statistics of a student with history', games.gameStatisticsSchema, await bobur('GET', '/student/games/statistics'));
} finally {
  await vite.close();
}

console.log(`\n${passed} passed, ${failures.length} failed`);
if (failures.length) {
  console.log(failures.join('\n'));
  process.exit(1);
}
process.exit(0);
