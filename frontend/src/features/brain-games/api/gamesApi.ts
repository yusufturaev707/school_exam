import { z } from 'zod';
import { request } from '@/lib/http';
import {
  achievementSchema,
  answerResponseSchema,
  dailyChallengeSchema,
  dailyQuestionSchema,
  gameCategoryInfoSchema,
  gameResultSchema,
  gameSchema,
  gameSessionSchema,
  gameStatisticsSchema,
  resumeGameResponseSchema,
  startGameResponseSchema,
  type GameDifficulty,
} from '../types';

const enc = encodeURIComponent;

export const gamesApi = {
  list: () => request(z.object({ games: z.array(gameSchema) }), { method: 'GET', url: '/games' }).then((r) => r.games),
  categories: () => request(z.object({ categories: z.array(gameCategoryInfoSchema) }), { method: 'GET', url: '/games/categories' }).then((r) => r.categories),
  get: (slug: string) => request(z.object({ game: gameSchema }), { method: 'GET', url: `/games/${enc(slug)}` }).then((r) => r.game),

  /** The backend generates the content; answers for assessed games never leave the server. */
  start: (gameId: string, difficulty: GameDifficulty, daily: boolean) =>
    request(startGameResponseSchema, { method: 'POST', url: `/games/${enc(gameId)}/start`, data: { difficulty, daily } }),

  /** Server checks the answer and returns feedback. Only the first answer to a question counts. */
  answer: (sessionId: string, questionId: string, optionId: string) =>
    request(answerResponseSchema, { method: 'POST', url: `/games/sessions/${enc(sessionId)}/answer`, data: { questionId, optionId }, timeout: 10_000 }),

  /**
   * Idempotent on the backend: repeating it returns the stored result, never a second reward.
   * `payload` carries game-specific evidence (e.g. the memory move log) — never a score.
   */
  complete: (sessionId: string, idempotencyKey: string, payload: Record<string, unknown> = {}) =>
    request(gameResultSchema, { method: 'POST', url: `/games/sessions/${enc(sessionId)}/complete`, data: payload, headers: { 'Idempotency-Key': idempotencyKey } }),

  /** Unfinished session for "Davom ettirish" after a reload (409 if it is already completed/abandoned). */
  resume: (sessionId: string) => request(resumeGameResponseSchema, { method: 'GET', url: `/games/sessions/${enc(sessionId)}` }),
  /** Closes a session the student left, so it never stays open on the server. Idempotent. */
  abandon: (sessionId: string) => request(z.object({ session: gameSessionSchema }), { method: 'POST', url: `/games/sessions/${enc(sessionId)}/abandon` }),

  dailyQuestion: () => request(dailyQuestionSchema, { method: 'GET', url: '/games/daily-question' }),
  answerDailyQuestion: (questionId: string, optionId: string) =>
    request(dailyQuestionSchema, { method: 'POST', url: '/games/daily-question/answer', data: { questionId, optionId } }),

  result: (sessionId: string) => request(gameResultSchema, { method: 'GET', url: `/games/sessions/${enc(sessionId)}/result` }),
  daily: () => request(dailyChallengeSchema, { method: 'GET', url: '/games/daily-challenge' }),
  statistics: () => request(gameStatisticsSchema, { method: 'GET', url: '/student/games/statistics' }),
  achievements: () => request(z.object({ achievements: z.array(achievementSchema) }), { method: 'GET', url: '/student/achievements' }).then((r) => r.achievements),
};
