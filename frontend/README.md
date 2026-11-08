# Bilimdon — online exam platform for students aged 10–13

React + TypeScript + Vite + Tailwind CSS v4, TanStack Query, Zustand, React Hook Form + Zod, Motion, KaTeX.

## Run

```bash
npm install
npm run dev:mock   # UI + in-browser mock backend (no server needed)
npm run dev        # UI against a real backend, proxied from /api → VITE_API_PROXY (default http://localhost:8000)
npm test           # unit tests (exam clock, autosave engine, QR token parsing)
npm run build      # type-check + production build (refuses to build with VITE_USE_MOCKS=true)
```

### Mock backend API (real HTTP, port 8000)

`postman/mocks/bilimdon-api/` is a stateful mock of the whole [API contract](docs/api-contract.md): HttpOnly session cookie, rate-limited login, single-use expiring QR tokens, server-side exam deadlines with a background sweeper, `clientSeq` answer ordering, idempotent submit, and per-student data isolation.

```bash
npm run mock:api        # Postman CLI: postman mock run … (port 8000)
npm run mock:api:node   # same server with plain Node
npm run dev             # second terminal — the /api proxy now reaches the mock
npm run mock:data       # re-export questions after editing src/mocks/questionBank.ts
```

| JSHSHIR | Student | State |
|---|---|---|
| `12345678901234` | Aziz | exam available |
| `23456789012345` | Malika | exam available |
| `34567890123456` | Bobur | exam already completed (has result + history) |

QR: `demo-qr-valid-7f3a9c2e1b4d` (single-use), `demo-qr-expired-0c8e2a9f71`, `demo-qr-used-5b1d7e3c9a20`, or mint a fresh one with
`POST /api/dev/qr-tokens {"jshshir":"…"}`. Reset all state: `POST /api/dev/reset` (both need header `X-Requested-With: XMLHttpRequest`).
Env knobs: `MOCK_EXAM_SECONDS=90` (fast auto-submit), `MOCK_FAIL_RATE=0.3` (random 503s on answer saves to test retry), `MOCK_REVIEW=0` (hide question review), `MOCK_GRACE_SECONDS`.

In-browser mock mode credentials: JSHSHIR `12345678901234`; the QR screen has buttons that simulate valid / expired / used / foreign QR codes.
Set `VITE_MOCK_EXAM_SECONDS=90` in `.env.mock` to test automatic submission quickly.
Use DevTools → Network → Offline to test the offline banner and answer retry.

## What is built (phase 1 + core screens)

The spec asks to establish the visual system on five core screens first. Implemented:

1. **Login** — welcome/method chooser, JSHSHIR form, QR scanner (camera only after the student opts in; BarcodeDetector with lazy jsQR fallback).
   Ticket link `/qr#t=<token>`: a phone camera opens it and the pupil is signed in without the scanner (asks first if someone else is signed in on the device). Try it in mock mode: `/qr#t=demo-qr-valid-7f3a9c2e1b4d`.
2. **Dashboard** — greeting + mascot, prominent exam card (Start / Continue / View result), subject cards, real stats or an encouraging empty state, recent activity.
3. **Exam introduction & “Kichik kelishuvimiz” agreement.**
4. **Exam interface** — sticky timer/progress header, question card with KaTeX and zoomable images, radio-based answer cards, subject-grouped navigator (bottom sheet on phones, sidebar on desktop), submit confirmation, offline banner, autosave status.
5. **Completion & results** — celebration, overall score ring, correct/incorrect/unanswered, subject analysis with supportive messages, question review when backend policy allows.

Also present: results history, profile + logout, help/privacy, 404, error/empty states.

## Bilimlar laboratoriyasi (brain games)

`src/features/brain-games/` contains the lab home with the daily challenge, featured games, categories, recently played and achievements. It also has the category, statistics, achievements and result pages, and the full-screen game page.

- **Engines** (`engines/`): each game is its own lazily loaded module behind `engines/registry.ts`, with logic separated from the view.
  - **Memory Cards:** a pure reducer, unit-tested.
  - **Missing Number** and **Pattern Master:** server-checked rounds via `hooks/useQuizRound`.
- **Shared flow:** intro and instructions → level → play → completion → replay. Completion uses one `Idempotency-Key` per session and retries.
- **Coming next:** Odd One Out, Quick Math and Maze are already in the catalogue as "Tez orada" cards.
- **Contract:** see the [API contract](docs/api-contract.md) (§Brain games). The backend logic for both mocks is in `src/mocks/games/` and is unit-tested. `npm run mock:data` builds it to CJS for the HTTP mock (it also runs automatically before `mock:api`).

## Exam reliability model

- Backend is the only clock: the UI computes remaining time from `expiresAt` and a measured server/device clock offset (`features/examination/utils/time.ts`), resynced every minute and on reconnect/focus.
- Every selection is autosaved through `AnswerSyncEngine` (retry with backoff, monotonic `clientSeq` so stale retries can't overwrite newer choices). Unconfirmed answers survive a refresh via `sessionStorage`.
- At the deadline the UI locks answers, flushes, and submits with a persistent `Idempotency-Key`; unsent answers ride along in the submit body. The backend must still finalise expired attempts on its own (see `docs/api-contract.md`).

## Structure

```
src/
  app/          config, providers, router, layouts
  components/   ui/ (design system), shared/ (Mascot, RichContent, subjects), feedback/
  features/     auth · dashboard · examination · results · activities · profile
  lib/          http (axios + error normalisation + zod validation), queryClient, date
  mocks/        DEV-ONLY mock backend (axios adapter) — never in production bundles
  styles/       Tailwind theme tokens
docs/api-contract.md   proposed backend contract
```

## Security notes

- No tokens or student data in localStorage; session is an HttpOnly cookie owned by the backend.
- JSHSHIR is never displayed after login, never logged, and the request body is excluded from error objects.
- Correct answers exist only in backend responses for results (when allowed) — and in `src/mocks`, which is dev-only.
- Post-login redirects are restricted to in-app paths.
