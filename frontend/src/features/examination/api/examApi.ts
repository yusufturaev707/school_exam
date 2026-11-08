import { z } from 'zod';
import { request } from '@/lib/http';
import {
  attemptSessionSchema,
  attemptStateSchema,
  examSummarySchema,
  saveAnswerResponseSchema,
  startAttemptResponseSchema,
  submitResponseSchema,
  type AttemptSession,
  type SubmitReason,
} from '../types';
import { computeClockOffset } from '../utils/time';

export interface LoadedAttempt {
  session: AttemptSession;
  /** serverNow − deviceNow, in ms. Add to Date.now() to get server time. */
  clockOffsetMs: number;
}

export const examApi = {
  listAvailable: () => request(z.object({ examinations: z.array(examSummarySchema) }), { method: 'GET', url: '/examinations/available' }).then((r) => r.examinations),

  /** Backend creates the attempt (or returns the already-active one) and records started_at / expires_at. */
  start: (examId: string) => request(startAttemptResponseSchema, { method: 'POST', url: `/examinations/${encodeURIComponent(examId)}/start` }),

  /**
   * Pass the questions already on screen to skip downloading them again: they don't change during
   * an attempt and carry their pictures inline, so they are by far the largest part of the answer.
   */
  async getAttempt(attemptId: string, knownQuestions?: AttemptSession['questions']): Promise<LoadedAttempt> {
    const url = `/examinations/attempts/${encodeURIComponent(attemptId)}`;
    const sentAt = Date.now();
    let session: AttemptSession;
    if (knownQuestions) {
      const state = await request(attemptStateSchema, { method: 'GET', url: `${url}?questions=0` });
      // Like the full answer, a finished attempt has no questions.
      session = { ...state, questions: state.status === 'in_progress' ? knownQuestions : [] };
    } else {
      session = await request(attemptSessionSchema, { method: 'GET', url });
    }
    return { session, clockOffsetMs: computeClockOffset(session.serverTime, sentAt, Date.now()) };
  },

  /**
   * Idempotent per (question, clientSeq): the backend must ignore writes whose clientSeq is
   * lower than the last stored one, so a slow retry can never overwrite a newer choice.
   */
  saveAnswer: (attemptId: string, questionId: string, selectedOptionIds: string[], clientSeq: number) =>
    request(saveAnswerResponseSchema, {
      method: 'PUT',
      url: `/examinations/attempts/${encodeURIComponent(attemptId)}/answers/${encodeURIComponent(questionId)}`,
      data: { selectedOptionIds, clientSeq },
      timeout: 10_000,
    }),

  /**
   * Safe to repeat: the Idempotency-Key makes the backend finalise the attempt exactly once.
   * `unsavedAnswers` carries choices that autosave could not deliver yet; the backend applies them
   * (respecting clientSeq) only if they arrive within its deadline grace policy.
   */
  submit: (attemptId: string, reason: SubmitReason, idempotencyKey: string, unsavedAnswers: Array<{ questionId: string; selectedOptionIds: string[]; clientSeq: number }>) =>
    request(submitResponseSchema, {
      method: 'POST',
      url: `/examinations/attempts/${encodeURIComponent(attemptId)}/submit`,
      data: { reason, unsavedAnswers },
      headers: { 'Idempotency-Key': idempotencyKey },
    }),
};
