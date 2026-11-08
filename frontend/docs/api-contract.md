# Bilimdon — proposed backend API contract

Frontend expectations for the backend. These are **proposals to agree on**, not a description of an existing service.
Runtime shapes are validated with zod in `src/features/*/types` — those schemas are the source of truth for field names.

## Conventions

- Base path `/api`, JSON, same origin as the frontend (so HttpOnly cookies work without CORS credentials gymnastics).
- **Session:** an `HttpOnly; Secure; SameSite=Lax` (or `Strict`) cookie set by the login endpoints. The frontend never sees a token.
- **CSRF:** state-changing requests carry `X-Requested-With: XMLHttpRequest`; the backend should additionally use a CSRF token or strict SameSite.
- **Errors:** `{ "code": "MACHINE_CODE", "message": "debug text" }` with a meaningful HTTP status. The UI maps `code` to child-friendly Uzbek text and never shows `message`.
- All timestamps are ISO-8601 UTC.

## Auth

| Method | Path | Body | Success | Errors |
|---|---|---|---|---|
| POST | `/auth/jshshir` | `{ jshshir: "14 digits" }` | `{ student }` + Set-Cookie | 401 `INVALID_CREDENTIALS`, 429 `RATE_LIMITED` |
| POST | `/auth/qr` | `{ token }` | `{ student }` + Set-Cookie | 401 `QR_INVALID`, 410 `QR_EXPIRED`, 409 `QR_ALREADY_USED`, 429 |
| GET | `/auth/me` | — | `{ student }` | 401 when no session |
| POST | `/auth/logout` | — | `{ ok: true }` (clears cookie) | — |

`student` = `{ id, firstName, lastName, className?, schoolName?, photoUrl? }` — **never** includes JSHSHIR.
`className` and `schoolName` come from the pupil's class and school. A pupil whose class, school, district or region is switched off cannot log in, and a running session ends (401).

QR tokens: cryptographically random (≥128 bits), short-lived, single-use, bound to one student (and optionally one exam session), validated and consumed atomically server-side. Never derived from JSHSHIR or a student id. Tickets encode a link to the app's `/qr` page with the token in the fragment, `https://<app>/qr#t=<token>`: a phone camera opens it and the page signs the pupil in. The fragment never reaches a server (requests, logs, Referer), and the page removes it from the address bar. The in-app scanner accepts the same link or a raw token. Never put the token in the query string (`?t=`).
Rate-limit both login endpoints per IP and per identifier.

## Dashboard & results

- `GET /student/dashboard` → `{ student: { firstName }, examinations: ExamSummary[], stats, recentActivity[] }`. `stats.overallPercent` and subject percents are `null` until a result exists.
- `GET /student/results` → `{ results: ResultSummary[] }` (newest first)
- `GET /student/results/{resultId}` → `ExamResult`. Must 403/404 for another student's result.
  `review.items` (with correct answers and explanations) is included **only** when exam policy allows; otherwise `review: { enabled: false }`.

## Examination

- `GET /examinations/available` → `{ examinations: ExamSummary[] }`
  `ExamSummary.status`: `available | in_progress | completed | unavailable`, plus `activeAttemptId`, `resultId`.
  Lists only exams assigned to this student (by region, district, school, class or grade), plus any exam they have already started. An unassigned exam is a 404 on `start`.
- `POST /examinations/{examId}/start` → `{ attemptId }`
  Creates the attempt, records `started_at`, computes `expires_at = started_at + duration`. If an active attempt exists, returns it (no second attempt). Errors: 409 `ALREADY_COMPLETED`, 403 `EXAM_NOT_AVAILABLE`.
- `GET /examinations/attempts/{attemptId}` → `AttemptSession`
  `{ id, examId, examTitle, status, startedAt, expiresAt, serverTime, sections, questions, answers, resultId }`.
  `questions[]` contain **no correct answers**. `prompt`, `passage`, option `content` and review `explanation` are content blocks: the backend sends `[{ type: "html", html }]` with sanitised HTML from the admin's editor, where formulas are plain text between `$...$`, `$$...$$`, `\\(...\\)` or `\\[...\\]`. Empty optional texts are `null`. `answers` = `{ [questionId]: optionId[] }`. `serverTime` lets the client correct for a wrong device clock.
  Images are inside that HTML as `data:image/webp;base64,…` (or `data:image/svg+xml,…`) URIs, never links, so `questions` is the heavy part. With `?questions=0` the same object comes back without the `questions` key; the client loads questions once and uses this for its periodic re-sync.
  `questions` come in this pupil's order, grouped by section. When the exam shuffles, `number` is the pupil's own position (1…N) and option `label`s are re-lettered A, B, C… in the order sent, so two pupils' numbers and letters differ; the review in `GET /student/results/{id}` uses the same order and letters. Options are always identified by `id`, never by label.
- `PUT /examinations/attempts/{attemptId}/answers/{questionId}` body `{ selectedOptionIds: string[], clientSeq: number }` → `{ questionId, savedAt }`
  Store only if `clientSeq` ≥ the stored one (out-of-order retries must not overwrite newer choices). 409 `ATTEMPT_CLOSED` after the deadline or finalisation; 422 for unknown option ids.
- `POST /examinations/attempts/{attemptId}/submit` header `Idempotency-Key: <uuid>`, body `{ reason: "manual" | "timeout", unsavedAnswers: [{ questionId, selectedOptionIds, clientSeq }] }` → `{ attemptId, status, resultId }`
  Finalises exactly once. Repeats (same or different key) return the same final state. `unsavedAnswers` are applied (respecting `clientSeq`) only if received before `expires_at + grace`.

### Deadline policy (backend responsibility)

The backend finalises any `in_progress` attempt once `now > expires_at + grace` (scheduled job and/or on next access), saving the answers it has and computing the result — even if the browser never calls submit. Scores are computed only on the server.

## Brain games — "Bilimlar laboratoriyasi"

Reference implementation: `src/mocks/games/gameServer.ts` (shared by both mocks). Response shapes: `src/features/brain-games/types` (zod). Fields are camelCase like the rest of this contract.

| Method | Path | Notes |
|---|---|---|
| GET | `/games` | Catalogue. Each game has `kind` (which client engine renders it), `difficulties`, `intro`, `instructions` (admin-editable copy), `isActive`, and the student's own `completedCount`. |
| GET | `/games/categories` | `memory · logic · math · attention · spatial · language` with `gameCount` / `activeCount`. |
| GET | `/games/{slug}` | One game. |
| POST | `/games/{id}/start` | Body `{ difficulty, daily }`. **The server generates the content** and returns `{ session, content }`; `content` is game-specific (`kind: memory \| missing-number \| pattern`). Correct answers and explanations are **not** included. `isDaily` is set only for today's game and level, and only until the daily challenge is earned. 409 `GAME_NOT_AVAILABLE` for inactive games. |
| POST | `/games/sessions/{id}/answer` | Body `{ questionId, optionId }` → `{ correct, correctOptionId, explanation, score, correctAnswers }`. The first answer counts; repeats return the stored verdict. Correct is +10 and wrong is 0; scores never go negative. |
| POST | `/games/sessions/{id}/complete` | Header `Idempotency-Key`. Body carries game-specific evidence, **never a score**. For memory it is `{ moves: [[cardId, cardId], …] }`, which the server replays and rejects with 422 `INVALID_MOVES` if the log does not solve the board. Idempotent: repeats return the same result and give no second reward. Response includes `newAchievements` and `isDaily`. |
| GET | `/games/sessions/{id}/result` | Stored result. Includes `bonus` (daily-challenge stars, separate from `score`). |
| GET | `/games/sessions/{id}` | Resume an **unfinished** session after a reload: `{ session, content, answers: [{ questionId, optionId, correct, correctOptionId, explanation }] }` — only the already-answered questions reveal their answer. 409 `SESSION_COMPLETED` / `SESSION_ABANDONED`. |
| POST | `/games/sessions/{id}/abandon` | The student left or restarted. Idempotent; the session can no longer be answered or completed (409 `SESSION_ABANDONED`) and earns nothing. Sessions nobody closes are dropped after a day. |
| GET | `/games/daily-challenge` | `{ date, game, difficulty, completed, completedAt, bonus }`. One game per day (Tashkent calendar day), rewarded once. Completing it adds `bonus` stars (20) to that session's result — exactly once, even if two daily sessions were started in parallel. **No streaks.** |
| POST | `/games/daily-challenge/complete` | Body `{ sessionId }`. Explicit form; completing a daily session already records it. |
| GET | `/games/daily-question` | Question of the day: `{ date, question: { id, prompt, sequence, options: [{ id, label }] }, points, answer }`. `answer` is `null` until the student replies, then `{ selectedOptionId, correct, correctOptionId, explanation, pointsEarned, answeredAt }` — so a reload shows the stored result. The correct option is never sent before the answer. |
| POST | `/games/daily-question/answer` | Body `{ questionId, optionId }` → same shape as GET. **Only the first answer of the day counts**; repeats return it. A correct answer gives `points` (5) stars. 422 `INVALID_ANSWER`. |
| GET | `/student/games/statistics` | The student's own totals, per category, per game (own best), and recent sessions (`score` + `bonus`). `totalScore` = game points + daily bonuses + question-of-the-day points — the ⭐ shown in the header. |
| GET | `/student/achievements` | All achievements with `unlockedAt`, `progress { current, target }` and `comingSoon` (needs games that are not playable yet — shown locked as "Tez orada" and left out of the "x / y" count). They reward participation and exploration only. |

Rules:
- Every session belongs to one student. Any other student gets 404, never 403, so the session's existence is not revealed.
- Scores are progress indicators only. There are no public rankings or comparisons, and nothing is presented as an IQ measure.
- Memory content is not secret, because it is a practice game. It is still verified by replaying the moves server-side. Quiz-type games keep their answers on the server until each question is answered.
- Admin content management (future): the catalogue copy, difficulty levels, question banks, explanations, durations and the daily schedule live in the backend. The frontend renders whatever `content` it receives for a known `kind`.
