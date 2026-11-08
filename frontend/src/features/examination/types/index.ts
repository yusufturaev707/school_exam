import { z } from 'zod';
import { contentSchema } from '@/types/content';
import { subjectCodeSchema } from '@/types/subject';

export const examSectionSchema = z.object({
  subject: subjectCodeSchema,
  title: z.string(),
  questionCount: z.number().int().nonnegative(),
});
export type ExamSection = z.infer<typeof examSectionSchema>;

/** Exam as listed on the dashboard / exam tab. All configuration comes from the backend. */
export const examSummarySchema = z.object({
  id: z.string(),
  title: z.string(),
  description: z.string(),
  totalQuestions: z.number().int().positive(),
  durationMinutes: z.number().int().positive(),
  sections: z.array(examSectionSchema),
  status: z.enum(['available', 'in_progress', 'completed', 'unavailable']),
  activeAttemptId: z.string().nullable(),
  resultId: z.string().nullable(),
  availableFrom: z.string().nullable().optional(),
});
export type ExamSummary = z.infer<typeof examSummarySchema>;

export const answerOptionSchema = z.object({
  id: z.string(),
  label: z.string(),
  content: contentSchema,
});
export type AnswerOption = z.infer<typeof answerOptionSchema>;

/**
 * `type` is an open string so new question types (multiple_choice, ordering…) can be added
 * by registering a renderer, without changing the engine. Correct answers are never part of this payload.
 */
export const questionSchema = z.object({
  id: z.string(),
  number: z.number().int().positive(),
  subject: subjectCodeSchema,
  type: z.string(),
  prompt: contentSchema,
  passage: contentSchema.nullable().optional(),
  options: z.array(answerOptionSchema),
});
export type Question = z.infer<typeof questionSchema>;

export const attemptStatusSchema = z.enum(['in_progress', 'submitted', 'expired']);
export type AttemptStatus = z.infer<typeof attemptStatusSchema>;

/** Selected option ids per question id. An array keeps multiple-choice possible later. */
export const answersSchema = z.record(z.string(), z.array(z.string()));
export type Answers = z.infer<typeof answersSchema>;

export const attemptSessionSchema = z.object({
  id: z.string(),
  examId: z.string(),
  examTitle: z.string(),
  status: attemptStatusSchema,
  startedAt: z.string(),
  /** Authoritative deadline computed by the backend. */
  expiresAt: z.string(),
  /** Backend clock at response time — used to correct for a wrong device clock. */
  serverTime: z.string(),
  sections: z.array(examSectionSchema),
  questions: z.array(questionSchema),
  answers: answersSchema,
  resultId: z.string().nullable(),
});
export type AttemptSession = z.infer<typeof attemptSessionSchema>;

export const startAttemptResponseSchema = z.object({ attemptId: z.string() });

export const saveAnswerResponseSchema = z.object({ questionId: z.string(), savedAt: z.string() });

export const submitResponseSchema = z.object({
  attemptId: z.string(),
  status: attemptStatusSchema,
  resultId: z.string().nullable(),
});
export type SubmitResponse = z.infer<typeof submitResponseSchema>;

export type SubmitReason = 'manual' | 'timeout';
